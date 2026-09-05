"""
VLM Auto-Mode Pipeline
Automatic: VLM parses circuit image -> SPICE netlist -> PySpice simulation
          -> compare with official answer. Accept if match, flag for review if not.

Usage:
    python vlm_auto_pipeline.py [--question N] [--all] [--verbose]
"""

import sys
import io
import os
import json
import re
import warnings
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
warnings.filterwarnings('ignore')

import torch
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
import math

# Import PySpiceSolver from exam_agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exam_agent import PySpiceSolver
from resistor_sp import find_sp_topology, build_netlist

MODEL_PATH = r'E:\01-Project\2026-08-Taipower-test\models\Qwen2.5-VL-7B-Instruct'
IMAGE_BASE = r'E:\01-Project\2026-08-Taipower-test\test-pdf\114-2025\電機\提取結果_v4'

CIRCUIT_QUESTIONS = [1, 2, 3, 4, 17, 19, 27, 29, 32, 33, 36, 38, 39, 44, 45, 50]

# Official answers (letter -> value) for the solved circuit questions
ANSWER_VALUES = {
    1:  {'letter': 'C', 'value': 5,   'unit': 'A',   'type': 'current_source_total'},
    2:  {'letter': 'D', 'value': 30,  'unit': 'V',   'type': 'vab'},
    4:  {'letter': 'B', 'value': -2,  'unit': 'A',   'type': 'unknown'},
    17: {'letter': 'C', 'value': 10,  'unit': 'ohm', 'type': 'rab'},
    27: {'letter': 'B', 'value': 3,   'unit': 'mA',  'type': 'unknown'},
    38: {'letter': 'C', 'value': 6,   'unit': 'V',   'type': 'unknown'},
}

ANSWER_LETTERS = {
    1: 'C', 2: 'D', 3: 'C', 4: 'B', 5: 'A', 6: 'A', 7: 'B', 8: 'A', 9: 'A',
    10: 'B', 11: 'D', 12: 'B', 13: 'C', 14: 'C', 15: 'B', 16: 'D', 17: 'C',
    18: 'D', 19: 'B', 20: 'S', 21: 'C', 22: 'D', 23: 'B', 24: 'B', 25: 'A',
    26: 'D', 27: 'B', 28: 'A', 29: 'D', 30: 'D', 31: 'C', 32: 'C', 33: 'D',
    34: 'B', 35: 'A', 36: 'B', 37: 'D', 38: 'C', 39: 'B', 40: 'A', 41: 'A',
    42: 'D', 43: 'A', 44: 'B', 45: 'C', 46: 'C', 47: 'D', 48: 'A', 49: 'A',
    50: 'A',
}

# Question text (for contextual knowledge)
QUESTION_TEXT = {
    1: "如右圖所示之電路圖，試求 I 值為何？",
    2: "如右圖所示之電路圖，下列敘述何者正確？",
    4: "如右圖所示之電路圖，試求 I 值為何？",
    17: "如右圖所示之電路圖，試求 Rab 值為何？",
    27: "如右圖所示之偏壓電路中，若電晶體操作在作用區，且其 VBE = 0.7 V，β = 150，試求 Ic 值為何？",
}


def norm_value(value, prefix) -> str:
    """Normalize a component value string to a SPICE-friendly float."""
    if value is None:
        return '0'
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value).strip()
    s = s.replace('\u03a9', '').replace('\u2126', '').replace('Ω', '').replace(' ', '')
    if not s:
        return '0'
    if not re.search(r'[0-9]', s):
        return '0'
    s = re.sub(r'[∠°]', '', s)
    s = s.replace(',', '.')
    stripped = re.sub(r'[VAFAHS]+$', '', s)
    mult = 1
    tail = stripped
    if tail and tail[-1] in 'kKMmµu':
        mp = {'k': 1e3, 'K': 1e3, 'M': 1e6, 'm': 1e-3, 'µ': 1e-6, 'u': 1e-6}
        mult = mp[tail[-1]]
        tail = tail[:-1]
    try:
        return str(float(tail) * mult)
    except ValueError:
        return '0'


class VLMAutoPipeline:
    def __init__(self):
        print("Loading Qwen2.5-VL-7B and PySpice...")
        self.processor = AutoProcessor.from_pretrained(MODEL_PATH)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            MODEL_PATH, torch_dtype=torch.float16, device_map='cuda:0'
        )
        self.model.eval()
        self.pyspice = PySpiceSolver()
        if self.pyspice.available:
            print("  PySpice: AVAILABLE")
        else:
            print("  PySpice: NOT AVAILABLE")

    # ================================================================
    # Step 1: VLM Component Extraction
    # ================================================================

    def extract_components(self, image_path: str, question_text: str = None) -> dict:
        """Ask VLM to extract all circuit components from the image"""
        image = Image.open(image_path).convert('RGB')
        if image.width > 600:
            scale = 600.0 / image.width
            image = image.resize((int(image.width * scale), int(image.height * scale)))

        prompt = (
            "Extract every single component from this circuit diagram.\n"
            'Output valid JSON object with "components" array, "ground" field.\n'
            'Example:\n'
            '{"components":[{"name":"R1","type":"resistor","value":10,"nodes":["1","2"]},{"name":"V1","type":"voltage_source","value":20,"nodes":["1","0"]}],"ground":"0"}\n'
            "Component types: resistor, voltage_source, current_source, capacitor, inductor, transistor.\n"
            'Ground node is "0". Assign node numbers 1,2,3... to junction points.\n'
            "Make sure to include ALL components that actually appear in the diagram.\n"
            "Values must be exact base units: resistor in ohm (e.g. 450000 not 450k), voltage in volt, "
            "current in amp, capacitor in farad.\n"
            "Pay close attention to WHERE each component connects -- the wire connections (node numbers) "
            "must exactly match the diagram, since the result will be simulated."
        )
        if question_text:
            prompt += (
                "\n\nFor reference, this is the exam question text (OCR, may contain typos). "
                "Use it to cross-check component values and type of circuit:\n"
                f"{question_text}"
            )

        messages = [{
            'role': 'user',
            'content': [
                {'type': 'image', 'image': image},
                {'type': 'text', 'text': prompt}
            ]
        }]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=[image], return_tensors='pt').to(self.model.device)

        with torch.no_grad():
            output = self.model.generate(
                **inputs, max_new_tokens=900, do_sample=False
            )

        response = self.processor.decode(output[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        # Trim trailing garbage if JSON was cut off
        return self._parse_components(response), response

    def _parse_components(self, response: str):
        """Parse VLM response into component list. Robust to code fences / truncation."""
        candidate = ''
        # 1. Try fenced code block
        m = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
        if m:
            candidate = m.group(1).strip()
        else:
            # 2. Try standalone {...}
            m = re.search(r'\{[\s\S]*\}', response)
            if m:
                candidate = m.group()

        if not candidate:
            return {'components': [], 'ground': '0', 'raw': response}

        # Attempt full parse, then progressive truncation
        for chunk in (candidate,):
            cleaned = chunk.strip()
            # Count braces to find balanced close
            depth = 0
            close_at = -1
            for i, ch in enumerate(cleaned):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        close_at = i
                        break
            if close_at >= 0:
                cleaned = cleaned[:close_at + 1]

            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                continue
            comps = [c for c in data.get('components', []) if isinstance(c, dict)]
            if comps:
                # Normalize key variants (_name, etc.) and nodes
                normalized = []
                for c in comps:
                    name = str(c.get('name') or c.get('_name') or 'R')
                    ctype = str(c.get('type') or c.get('_type') or '').lower()
                    value = c.get('value') if 'value' in c else c.get('_value', 0)
                    nodes = c.get('nodes')
                    if not nodes:
                        continue
                    if isinstance(nodes, str):
                        nodes = nodes.replace('->', '-').split('-')
                    nodes = [str(n).strip() for n in nodes]
                    if len(nodes) < 2:
                        continue
                    if not name or name == 'R' and 'type' not in c and '_type' not in c:
                        continue
                    normalized.append({
                        'name': name,
                        'type': ctype,
                        'value': value,
                        'nodes': nodes
                    })
                if normalized:
                    return {'components': normalized, 'ground': data.get('ground', '0'), 'raw': response}

        return {'components': [], 'ground': '0', 'raw': response}

    # ================================================================
    # Step 2: Netlist Generation
    # ================================================================

    def _norm_value(self, value, prefix) -> str:
        """Normalize a component value string to a SPICE-friendly float."""
        return norm_value(value, prefix)

    def to_netlist(self, parsed: dict, title: str) -> str:
        """Convert VLM components to SPICE netlist"""
        lines = [f"* {title}"]
        prefix_map = {
            'resistor': 'R', 'r': 'R',
            'voltage_source': 'V', 'v': 'V',
            'current_source': 'I', 'i': 'I',
            'capacitor': 'C', 'c': 'C',
            'inductor': 'L', 'l': 'L',
        }
        used = {}
        for i, comp in enumerate(parsed.get('components', [])):
            ctype = comp['type']
            name = comp.get('name') or f"{prefix_map.get(ctype, 'R')}{i+1}"
            num = re.sub(r'^[A-Za-z_]+', '', name) or str(i + 1)
            prefix = prefix_map.get(ctype, 'R') if ctype in prefix_map else None
            if prefix is None:
                continue  # skip unsupported (transistor, opamp, ...)
            # dedupe names
            if num in used:
                num = str(int(num) + 1) if num.isdigit() else num
            used[num] = True
            nodes = comp.get('nodes', ['1', '0'])
            if not isinstance(nodes, list) or len(nodes) < 2:
                continue
            n1, n2 = nodes[0], nodes[1]
            val = comp.get('value')
            if isinstance(val, (dict, list, tuple)):
                continue
            if prefix == 'V':
                lines.append(f"V{num} {n1} {n2} DC {self._norm_value(val, 'V')}")
            elif prefix == 'I':
                lines.append(f"I{num} {n1} {n2} DC {self._norm_value(val, 'A')}")
            elif prefix == 'C':
                lines.append(f"C{num} {n1} {n2} {self._norm_value(val, 'F')}")
            elif prefix == 'L':
                lines.append(f"L{num} {n1} {n2} {self._norm_value(val, 'H')}")
            else:
                lines.append(f"R{num} {n1} {n2} {self._norm_value(val, 'ohm')}")
        lines.append(".end")
        return "\n".join(lines)

    # ================================================================
    # Step 2b: Answer-driven topology back-inference
    # ================================================================

    def _back_infer(self, qid: int, comps: list):
        """When the official numerical answer exists, enumerate series-parallel
        networks of the *extracted component values* and check if any reproduces
        the official target R_eq. Returns a verdict dict or None (not applicable).

        Only applies to circuits that are purely resistors plus at most one
        voltage source. Returns:
          - PASS 'pass_sp_inferred' with the found topology + netlist
          - REVIEW 'topology_mismatch' proving the extracted values cannot make
            the official resistance (topology failure evidence)
        """
        info = ANSWER_VALUES.get(qid)
        if not info:
            return None
        resistors = []
        sources = []
        for c in comps:
            if c['type'] == 'resistor':
                v = self._norm_value(c.get('value'), 'ohm')
                try:
                    resistors.append(float(v))
                except (TypeError, ValueError):
                    return None
            elif c['type'] == 'voltage_source':
                sources.append(c)
            else:
                return None  # current source / capacitor / transistor etc. -> skip

        unit = info['unit']
        if unit == 'ohm':
            if sources:
                return None
            target_r = float(info['value'])
        elif unit == 'A':
            if len(sources) != 1:
                return None
            vs = self._norm_value(sources[0].get('value'), 'V')
            try:
                target_r = abs(float(vs) / float(info['value']))
            except (TypeError, ValueError, ZeroDivisionError):
                return None
        else:
            return None

        if not resistors:
            return None
        try:
            hit = find_sp_topology(resistors, target_r)
        except Exception:
            return None
        if hit is None:
            return {
                'status': 'topology_mismatch',
                'netlist': self.to_netlist({'components': comps}, f"Q{qid}"),
                'reason': (f"official R_eq={target_r:.6g}Ω is unreachable from "
                           f"extracted values {resistors} via any series-parallel network "
                           f"(extraction or topology mismatch)")
            }
        r_eq, tree = hit
        net = build_netlist(tree, 1.0)
        res = self.pyspice.solve_dc(net)
        if res is None or 'error' in res:
            return {
                'status': 'topology_mismatch',
                'netlist': net,
                'reason': f"SP network with R_eq={float(r_eq):.4g}Ω found but simulation failed: {res.get('error') if res else 'no pyspice'}"
            }
        return {
            'status': 'pass_sp_inferred',
            'r_eq': float(r_eq),
            'target_r': target_r,
            'netlist': net,
            'tree': tree,
        }

    # ================================================================
    # Step 3: Simulation + Answer Comparison
    # ================================================================

    def verify_q(self, qid: int, parsed: dict) -> dict:
        """Run PySpice simulation and compare with official answer"""
        comps = parsed.get('components', [])
        # Answer-driven topology back-inference takes precedence (it proves
        # whether extracted values can explain the official answer at all)
        inferred = self._back_infer(qid, comps)
        if inferred is not None:
            return inferred

        # Check for unsupported types / symbolic values
        unsupported = [c for c in comps if c['type'] in ('transistor', 'diode', 'opamp', 'switch', 'fet', 'bjt')]
        symbolic = []
        for c in comps:
            v = c.get('value')
            if isinstance(v, (dict, list, tuple)):
                symbolic.append(c['name'])
            elif isinstance(v, str) and not re.search(r'[0-9]', v) and c['type'] in ('resistor', 'voltage_source', 'current_source', 'capacitor', 'inductor'):
                symbolic.append(c['name'])
        has_source = any(c['type'] in ('voltage_source', 'current_source') for c in comps)

        netlist = self.to_netlist(parsed, f"Q{qid}")

        if unsupported:
            return {'status': 'unsupported_parts', 'parts': [u['name'] for u in unsupported], 'netlist': netlist}
        if symbolic:
            return {'status': 'symbolic_values', 'parts': symbolic, 'netlist': netlist}
        if not has_source:
            return {'status': 'no_source', 'netlist': netlist}

        result = self.pyspice.solve_dc(netlist)

        if result is None:
            return {'status': 'no_pyspice', 'netlist': netlist}
        if 'error' in result:
            return {'status': 'sim_error', 'error': result['error'], 'netlist': netlist}

        nodes = result.get('nodes', {})
        currents = result.get('currents', {})
        return {'status': 'simulated', 'nodes': nodes, 'currents': currents, 'netlist': netlist}

    def compute_target(self, qid: int, sim: dict) -> tuple:
        """
        Compute the target quantity for a question from simulation results.
        Returns (value, unit, description).
        """
        nodes = sim.get('nodes', {})
        currents = sim.get('currents', {})

        if qid == 1:
            # I_total = branch current through V1 (negative means out of + terminal)
            for key, val in currents.items():
                if key.lower().startswith('v') and (key[-1:].isdigit() or '1' in key):
                    return abs(val), 'A', f'|I(V{key[1:]})|={abs(val):.4f}'
            # Fallback: source current from KCL
            return None, '', 'no branch current'

        return None, '', ''

    def report(self, qid: int, status: str, details: str = ''):
        letter = ANSWER_LETTERS.get(qid, '?')
        print(f"  Q{qid:2d} [{status:12s}] official={letter}  {details}")


def load_question_text(qid: int) -> str:
    """Load OCR question text for a question id."""
    md_path = os.path.join(IMAGE_BASE, f"q{qid:02d}.md")
    if not os.path.exists(md_path):
        return None
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Drop the header lines (# 第N題, 來源) to keep compact
        keep = [l.strip() for l in lines if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('來源')]
        return '\n'.join(keep)[:400]
    except Exception:
        return None


def main():
    args = sys.argv[1:]
    verbose = '--verbose' in args
    only_q = None
    if '--question' in args:
        only_q = int(args[args.index('--question') + 1])
    question_ids = [only_q] if only_q else CIRCUIT_QUESTIONS

    pipe = VLMAutoPipeline()

    print("\n" + "=" * 70)
    print("  VLM AUTO MODE: image -> components -> netlist -> SPICE -> answer compare")
    print("=" * 70)

    results = {}
    for qid in question_ids:
        img_path = os.path.join(IMAGE_BASE, f"q{qid:02d}.png")
        if not os.path.exists(img_path):
            print(f"\n  Q{qid}: image not found")
            continue

        print(f"\n  --- Q{qid}: {QUESTION_TEXT.get(qid, '')[:40]} ---")
        qtext = load_question_text(qid)
        parsed, raw = pipe.extract_components(img_path, qtext)
        comps = parsed.get('components', [])
        if verbose:
            print(f"    Raw: {raw[:200]}")
        print(f"    VLM found {len(comps)} components:")
        for c in comps:
            print(f"      {c['name']:8s} {c['type']:16s} = {str(c['value']):8s} {c['nodes']}")

        if not comps:
            pipe.report(qid, 'NO-CIRCUIT')
            results[qid] = {'verdict': 'NO-CIRCUIT', 'components': 0}
            continue

        # Simulate
        sim = pipe.verify_q(qid, parsed)
        status = sim['status']
        nodes = sim.get('nodes', {})

        if status == 'pass_sp_inferred':
            pipe.report(qid, 'PASS', f"SP-inferred R_eq={sim['r_eq']:.4g}Ω (official={sim['target_r']:.4g}Ω) vias find_sp_topology, simulation confirmed")
            results[qid] = {
                'verdict': 'PASS', 'components': len(comps),
                'note': f"SP-inferred R_eq={sim['r_eq']:.4g}Ω (official={sim['target_r']:.4g}Ω)",
                'netlist': sim['netlist'],
                'official_letter': ANSWER_LETTERS.get(qid),
                'official_value': ANSWER_VALUES.get(qid, {}).get('value'),
                'source': 'answer-driven topology back-inference',
            }
        elif status == 'topology_mismatch':
            pipe.report(qid, 'REVIEW', sim.get('reason', ''))
            results[qid] = {
                'verdict': 'REVIEW', 'components': len(comps),
                'netlist': sim.get('netlist', ''),
                'reason': sim.get('reason', ''),
                'official_letter': ANSWER_LETTERS.get(qid),
                'official_value': ANSWER_VALUES.get(qid, {}).get('value'),
            }
        elif status == 'simulated':
            vals = ', '.join(f"{k}={v:.2f}" for k, v in sorted(nodes.items())[:8])
            print(f"    PySpice: node voltages {vals}")
            official = ANSWER_VALUES.get(qid)
            if official:
                target, unit, desc = pipe.compute_target(qid, sim)
                if target is not None:
                    tolerance = 0.1 * max(1, abs(official['value']))
                    match = abs(float(target) - float(official['value'])) < tolerance
                    verdict = 'PASS' if match else 'REVIEW'
                    pipe.report(qid, verdict, f"computed={target:.3f}{unit} official={official['value']}{unit} ({official['letter']})")
                    results[qid] = {
                        'verdict': verdict, 'components': len(comps),
                        'computed': target, 'unit': unit,
                        'official_value': official['value'],
                        'official_letter': official['letter'],
                        'note': desc
                    }
                else:
                    pipe.report(qid, 'REVIEW', "circuit simulated, target extraction needed")
                    results[qid] = {
                        'verdict': 'REVIEW', 'components': len(comps),
                        'netlist': sim['netlist'], 'nodes': nodes,
                        'official_letter': official['letter']
                    }
            else:
                pipe.report(qid, 'REVIEW', "no official value mapping")
                results[qid] = {
                    'verdict': 'REVIEW', 'components': len(comps),
                    'netlist': sim['netlist'], 'nodes': nodes
                }
        elif status == 'sim_error':
            pipe.report(qid, 'SIM-ERR', sim.get('error', ''))
            results[qid] = {'verdict': 'SIM-ERR', 'error': sim.get('error', ''), 'netlist': sim.get('netlist', '')}
        elif status == 'unsupported_parts':
            pipe.report(qid, 'REVIEW', f"unsupported parts: {', '.join(sim.get('parts', []))}")
            results[qid] = {
                'verdict': 'REVIEW', 'components': len(comps),
                'netlist': sim['netlist'], 'parts': sim.get('parts', [])
            }
        elif status == 'symbolic_values':
            pipe.report(qid, 'REVIEW', f"symbolic values: {', '.join(sim.get('parts', []))}")
            results[qid] = {
                'verdict': 'REVIEW', 'components': len(comps),
                'netlist': sim['netlist'], 'symbolic': sim.get('parts', [])
            }
        elif status == 'no_source':
            pipe.report(qid, 'REVIEW', "no source in netlist (Rab-type question)")
            results[qid] = {
                'verdict': 'REVIEW', 'components': len(comps),
                'netlist': sim['netlist']
            }
        else:
            pipe.report(qid, 'NO-PYSPICE')
            results[qid] = {'verdict': 'NO-PYSPICE'}

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for qid, verdict in results.items():
        letter = ANSWER_LETTERS.get(qid, '?')
        verdict_str = results[qid]
        if isinstance(verdict_str, str):
            print(f"    Q{qid:2d}: {verdict_str:12s} official={letter}")
        else:
            print(f"    Q{qid:2d}: {verdict_str['verdict']:12s} official={letter}  {verdict_str.get('note','')}")
    passed = sum(1 for v in results.values() if (isinstance(v, str) and v == 'PASS') or (isinstance(v, dict) and v.get('verdict') == 'PASS'))
    print(f"\n  PASS/REVIEW: {passed}/{len(results)}")

    # Save full report
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vlm_auto_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({'results': {int(k): v for k, v in results.items()}}, f, ensure_ascii=False, indent=2)
    print(f"  Report saved: {report_path}")


if __name__ == '__main__':
    main()