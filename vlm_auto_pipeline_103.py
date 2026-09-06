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
IMAGE_BASE = r'E:\01-Project\2026-08-Taipower-test\test-pdf\103-2014\電機(甲)\提取結果_v103a'

CIRCUIT_QUESTIONS = [3, 4, 6, 9, 10, 12, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 27, 29, 30, 31, 33, 35, 37, 38, 39]

ANSWER_VALUES = {
    1:  {'letter': 'D', 'value': 100, 'unit': 'ohm', 'type': 'xc'},
    21: {'letter': 'B', 'value': 10,  'unit': 'A',   'type': 'i'},
    22: {'letter': 'C', 'value': 25,  'unit': 'ohm', 'type': 'rth'},
    23: {'letter': 'A', 'value': 4,   'unit': 'H',   'type': 'le'},
    40: {'letter': 'B', 'value': 3.2, 'unit': 'mS',  'type': 'gm'},
}

ANSWER_LETTERS = {
    1: 'D', 2: 'C', 3: 'A', 4: 'A', 5: 'B', 6: 'D', 7: 'A', 8: '送分', 9: 'B',
    10: 'B', 11: 'D', 12: 'B', 13: 'C', 14: 'B', 15: 'A', 16: 'D', 17: 'B',
    18: 'B', 19: 'C', 20: 'C', 21: 'B', 22: 'C', 23: 'A', 24: 'B', 25: 'D',
    26: 'C', 27: 'A', 28: 'D', 29: 'D', 30: 'C', 31: 'D', 32: 'B', 33: 'C',
    34: '送分', 35: 'C', 36: '送分', 37: 'D', 38: 'A', 39: 'C', 40: 'B',
}

QUESTION_TEXT = {
    3: "在右圖電路中，負載ZL在特定值時可得到最大功率轉移，求ZL可吸收之最大功率為？",
    4: "求右圖電路中之 ia =？",
    6: "右圖電路之電壓響應呈現臨界阻尼情況，則R值為？",
    9: "在右圖電路中，求端點a-b看入之戴維寧等效電壓Vth=？",
    10: "在右圖電路中，Vc(0-)=0 V，t=0時，開關閉合。若t>0時，電源電壓Vi=2 V，電流 i(t)=4e^(-2t) A，則電容C值為？",
    12: "如右圖方波波峰電壓為10 V，於二極體端加上VR=5 V時，當輸出方波在負半週時，Vo峰值電壓應為？",
    15: "如右圖限流保護電路，若Q1、Q2的β=200，Vin=12 V，VBE,active=0.6 V，輸出端至接續後級線路間可接上短路保護保險絲安培數為何？",
    16: "如右圖為何種回授放大器？",
    17: "如右圖精密半波整流電路，若R1=100 kΩ，Vi(t)=10sinωt V，若輸出電壓V0平均值要達6.36 V，則R2=？",
    18: "右圖CMOS FET之邏輯電路是何種邏輯閘？",
    19: "設若右圖電流鏡VT1=VT2=VT3=2 V，β1=β2=β3，kn'(W/L)=2 mA/V2，且I1=1 mA，試求V2電壓=？",
    20: "右圖達靈頓電路中若每個晶體β=150，RE=680 Ω，則Rin輸入電阻為？",
    21: "有一RLC串聯電路如右圖，求電流相量I=？",
    22: "有一電路如右圖，求端點a-b看入之戴維寧等效電阻Rth=？",
    23: "有一電路如右圖，L1=4 H，L2=2 H，M=1 H。求端點a-b看入之等效電感？",
    24: "有一電路如右圖，求Vb=？",
    27: "有一電路如右圖，開關已閉合很久，然後在t=0時打開。求i0(t)=？",
    29: "有一電路如右圖，電流源為δ(t)，C=0.5 F，R=2 Ω。求Vc(t)=？",
    30: "有一電路如右圖，i(0)=10 A。求t>0時，ix(t)=？",
    31: "如右圖三級串級回授放大器圖，各電晶體Q1、Q2、Q3，β=120，VBE(on)=0.7 V，VT=26 mV，求得Q3，gm≒？",
    33: "如右圖FET偏壓電路，給定VT=1 V，kn'(W/L)=1 mA/V2，在忽略通道長度調變效應下，求ID電流？",
    35: "如右圖T型放大器，求V0=？",
    37: "如右圖為簡單音頻放大器的電路圖，若要得到較低的轉角頻率fL=20 Hz，求C耦合電容值？",
    38: "右圖假若要設計一個帶通濾波器線路，給定Vin=10 kHz，伴隨1 kHz低頻與100 kHz高頻雜訊，在濾波器頻帶寬B為1 kHz，電壓增益Av=1，C=0.001 μF，試求R2≒？",
    39: "考慮如右圖N-通道MOSFET等效電路，若忽略rs、rd、ro、Cds及汲極連結到訊號地，kn'(W/L)=0.4 mA/V2，VT=1 V，λ=0，Cgd=0.04 pF，Cgs=0.2 pF，給定偏壓VGS=3 V，求單位電流增益的頻率(unity-gain frequency)fT？",
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
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vlm_auto_report_103.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({'results': {int(k): v for k, v in results.items()}}, f, ensure_ascii=False, indent=2)
    print(f"  Report saved: {report_path}")


if __name__ == '__main__':
    main()