"""
VLM Circuit Diagram Parser
Uses Qwen2.5-VL-7B-Instruct to parse circuit diagrams from exam images.

Usage:
    python vlm_circuit_parser.py --image q01.png
    python vlm_circuit_parser.py --question 1
    python vlm_circuit_parser.py --all
"""

import sys
import io
import os
import json
import re
import warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
warnings.filterwarnings('ignore')

import torch
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

# ============================================================
# Model Configuration
# ============================================================

MODEL_PATH = r'E:\01-Project\2026-08-Taipower-test\models\Qwen2.5-VL-7B-Instruct'
IMAGE_BASE = r'E:\01-Project\2026-08-Taipower-test\test-pdf\114-2025\電機\提取結果_v4'


class VLMCircuitParser:
    """Parse circuit diagrams using Qwen2.5-VL"""

    def __init__(self):
        print("Loading Qwen2.5-VL-7B-Instruct...")
        self.processor = AutoProcessor.from_pretrained(MODEL_PATH)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float16,
            device_map='auto'
        )
        print(f"Model loaded on {self.model.device}")

    def parse_image(self, image_path: str) -> dict:
        """
        Parse a circuit diagram image and return structured component list.
        
        Returns:
            {
                "components": [
                    {"name": "V1", "type": "voltage_source", "value": 20, "nodes": ["1", "0"]},
                    {"name": "R1", "type": "resistor", "value": 10, "nodes": ["1", "2"]},
                    ...
                ],
                "ground": "0",
                "description": "...",
                "raw_response": "..."
            }
        """
        image = Image.open(image_path).convert('RGB')

        prompt = """You are an expert electrical engineer analyzing circuit diagrams.

Analyze this circuit diagram and extract ALL components with their values and connections.

For each component, identify:
1. Component name (R1, R2, V1, I1, C1, L1, etc.)
2. Component type (resistor, voltage_source, current_source, capacitor, inductor)
3. Component value (resistance in ohms, voltage in volts, current in amps, etc.)
4. Which two nodes it connects (label nodes as numbers: 1, 2, 3... and 0 for ground)

Rules:
- The ground/reference node is always labeled "0"
- Voltage sources: positive terminal first
- Current sources: direction from first node to second node
- Resistors: either order is fine

Output ONLY valid JSON (no markdown, no explanation):
{
  "components": [
    {"name": "V1", "type": "voltage_source", "value": 20, "nodes": ["1", "0"]},
    {"name": "R1", "type": "resistor", "value": 10, "nodes": ["1", "2"]}
  ],
  "ground": "0",
  "description": "Brief circuit description"
}"""

        messages = [
            {
                'role': 'user',
                'content': [
                    {'type': 'image', 'image': image},
                    {'type': 'text', 'text': prompt}
                ]
            }
        ]

        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(
            text=[text], images=[image], return_tensors="pt"
        ).to(self.model.device)

        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=0.1,
                do_sample=False
            )

        response = self.processor.decode(
            output[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )

        return self._parse_response(response)

    def _parse_response(self, response: str) -> dict:
        """Parse VLM response into structured data"""
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            return {
                'components': [],
                'ground': '0',
                'description': 'Failed to parse VLM response',
                'raw_response': response,
                'success': False
            }

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return {
                'components': [],
                'ground': '0',
                'description': 'Invalid JSON in VLM response',
                'raw_response': response,
                'success': False
            }

        # Normalize component data
        components = []
        for comp in data.get('components', []):
            name = comp.get('name', '')
            comp_type = comp.get('type', '').lower()

            # Normalize type names
            type_map = {
                'resistor': 'resistor', 'r': 'resistor',
                'voltage_source': 'voltage_source', 'v': 'voltage_source',
                'current_source': 'current_source', 'i': 'current_source',
                'capacitor': 'capacitor', 'c': 'capacitor',
                'inductor': 'inductor', 'l': 'inductor',
            }
            comp_type = type_map.get(comp_type, comp_type)

            # Normalize nodes
            nodes = comp.get('nodes', ['1', '0'])
            if isinstance(nodes, str):
                nodes = nodes.split('-')
            nodes = [str(n).strip() for n in nodes]
            if len(nodes) < 2:
                nodes = ['1', '0']

            components.append({
                'name': name,
                'type': comp_type,
                'value': comp.get('value'),
                'nodes': nodes
            })

        return {
            'components': components,
            'ground': data.get('ground', '0'),
            'description': data.get('description', ''),
            'raw_response': response,
            'success': len(components) > 0
        }

    def to_spice_netlist(self, parsed: dict, title: str = "VLM Circuit") -> str:
        """Convert parsed circuit to SPICE netlist"""
        lines = [f"* {title}"]
        lines.append(f"* Parsed by Qwen2.5-VL-7B-Instruct")

        for comp in parsed.get('components', []):
            name = comp['name']
            comp_type = comp['type']
            value = comp.get('value', 0)
            n1, n2 = comp.get('nodes', ['1', '0'])

            prefix_map = {
                'resistor': 'R',
                'voltage_source': 'V',
                'current_source': 'I',
                'capacitor': 'C',
                'inductor': 'L',
            }
            prefix = prefix_map.get(comp_type, 'R')

            # Generate SPICE line
            if comp_type == 'voltage_source':
                lines.append(f"{prefix}{name[1:] if len(name)>1 else '1'} {n1} {n2} DC {value}")
            elif comp_type == 'current_source':
                lines.append(f"{prefix}{name[1:] if len(name)>1 else '1'} {n1} {n2} DC {value}")
            else:
                lines.append(f"{prefix}{name[1:] if len(name)>1 else '1'} {n1} {n2} {value}")

        lines.append(".end")
        return "\n".join(lines)


# ============================================================
# Pre-defined answers for verification
# ============================================================

EXAM_ANSWERS = {
    1: {"answer": "C", "value": 5, "unit": "A"},
    6: {"answer": "A", "value": "R-L", "unit": ""},
    7: {"answer": "B", "value": 50, "unit": "Hz"},
    8: {"answer": "A", "value": 15, "unit": "W"},
    9: {"answer": "A", "value": "e^(-3t)(3cos2t-sin2t)", "unit": ""},
    10: {"answer": "B", "value": 0.60, "unit": ""},
    12: {"answer": "B", "value": 9.87, "unit": "A"},
    13: {"answer": "C", "value": 50, "unit": "uF"},
    14: {"answer": "C", "value": 2, "unit": "times"},
    15: {"answer": "B", "value": 900, "unit": "W"},
    21: {"answer": "C", "value": 13.6, "unit": "A"},
    23: {"answer": "B", "value": 20, "unit": "ohm"},
    24: {"answer": "B", "value": 40, "unit": "W"},
    25: {"answer": "A", "value": 0.45, "unit": "kWh"},
    28: {"answer": "A", "value": 80, "unit": ""},
    34: {"answer": "B", "value": 10, "unit": "mS"},
    44: {"answer": "B", "value": 2, "unit": "times"},
    46: {"answer": "C", "value": 16, "unit": "times"},
}


def main():
    parser = VLMCircuitParser()

    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            # Parse all questions with circuit images
            for qid in range(1, 51):
                img_path = os.path.join(IMAGE_BASE, f"q{qid:02d}.png")
                if os.path.exists(img_path):
                    print(f"\n{'='*60}")
                    print(f"  Q{qid}")
                    print(f"{'='*60}")
                    result = parser.parse_image(img_path)
                    print(f"  Components found: {len(result['components'])}")
                    for comp in result['components']:
                        print(f"    {comp['name']}: {comp['type']} = {comp['value']} ({comp['nodes']})")
                    if qid in EXAM_ANSWERS:
                        print(f"  Correct answer: {EXAM_ANSWERS[qid]['answer']}")

        elif sys.argv[1] == '--question':
            qid = int(sys.argv[2])
            img_path = os.path.join(IMAGE_BASE, f"q{qid:02d}.png")
            if os.path.exists(img_path):
                result = parser.parse_image(img_path)
                print(json.dumps(result, indent=2, ensure_ascii=False))
                print("\nSPICE Netlist:")
                print(parser.to_spice_netlist(result, f"Q{qid}"))
            else:
                print(f"Image not found: {img_path}")

        elif sys.argv[1] == '--image':
            img_path = sys.argv[2]
            if os.path.exists(img_path):
                result = parser.parse_image(img_path)
                print(json.dumps(result, indent=2, ensure_ascii=False))
                print("\nSPICE Netlist:")
                print(parser.to_spice_netlist(result))

    else:
        # Default: parse Q1
        img_path = os.path.join(IMAGE_BASE, "q01.png")
        print(f"Parsing: {img_path}")
        result = parser.parse_image(img_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\nSPICE Netlist:")
        print(parser.to_spice_netlist(result, "Q1"))


if __name__ == '__main__':
    main()
