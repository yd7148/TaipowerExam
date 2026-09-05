---
name: taipower-exam-report
description: Use when the user asks to generate a complete detailed answer report (整份考題詳細解答) for 國營事業/台電 exam PDFs from OCR-extracted questions, or build 電路學/電子學 circuit-diagram solutions from VLM component extraction + SPICE simulation + official answer matching. Covers the Qwen2.5-VL-7B pipeline (vlm_auto_pipeline.py), SP topology back-inference (resistor_sp.py), and the markdown report generators (build_full_report.py / build_full_exam.py). Use for naming report files "*- 114 年經濟部所屬事業機構新進職員甄試試題.md" and syncing to GitHub.
---

# Taipower Exam Report

End-to-end workflow: OCR-extracted exam questions → (for circuit diagrams) Qwen2.5-VL-7B component extraction → SP topologies back-inferred from values + official answer → ngspice/PySpice simulation → verdict (PASS/REVIEW/SIM-ERR) → merge with 完整解答.md into a complete detailed-answer markdown report.

## Directory Layout (114-2025 電機)

```
test-pdf/114-2025/電機/提取結果_v4/
  q01.png ... q50.png      # per-question cropped images
  q01.md  ... q50.md       # per-question OCR text
  完整解答.md               # all 50 題目/選項/官方答案/解題過程
  exam_pageN.png / answer_pageN.png
```

## Key Scripts (project root E:\01-Project\2026-08-Taipower-test)

- `vlm_auto_pipeline.py` — VLM auto pipeline: image → components → SP back-inference → SPICE → verdict.
  - `CIRCUIT_QUESTIONS = [1,2,3,4,17,19,27,29,32,33,36,38,39,44,45,50]`
  - `ANSWER_LETTERS` / `ANSWER_VALUES` hold the official key.
  - `resistor_sp.py` back-inference is wired in via `_back_infer`.
  - VLM = `Qwen2_5_VLForConditionalGeneration` (NOT AutoModelForVision2Seq), `max_new_tokens=900, do_sample=False`, image resized to 600px width, device_map='cuda:0'.
- `resistor_sp.py` — brute-force series/parallel topology search using `Fraction`; `test_sp.py` validates it (all pass).
- `build_full_report.py` — merges 完整解答.md + vlm_auto_report.json → `vlm_auto_report_full*.md` (only the 16 circuit questions).
- `build_full_exam.py` — merges *all 50 questions* (題目/選項/實際答案/解題過程 + VLM verdict for circuit Qs) → **`完整詳細解答- 114 年經濟部所屬事業機構新進職員甄試試題.md`**.
- `exam_agent.py` — main solver agent (SymPy/MNA/PySpice triple verification).

## Environment Gotchas (Windows)

- Output: wrap with `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` before printing Chinese/emoji.
- Import torch BEFORE HF/PySpice imports; set `KMP_DUPLICATE_LIB_OK='TRUE'` first.
- PySpice: `os.add_dll_directory(r'C:\ngspice\Spice64_dll\dll-vs')` + `r'C:\ngspice\Spice64\bin'`.
- **Never** call `ngspice -b x.cir` directly — it hangs after ~60s; always use PySpice `circuit.simulator()` (the `CircuitSimulator(circ)` class is deprecated, no `.SIMULATOR` attr).
- Branch keys are prefixed, e.g. source `V1` → branch `vv1`; use `str(key).endswith('v1')` to find it.

## Report Naming Convention

`.md` files on GitHub must follow: `<short description>- 114 年經濟部所屬事業機構新進職員甄試試題.md`
(e.g. `完整詳細解答- 114 年經濟部所屬事業機構新進職員甄試試題.md`).

## GitHub Sync

- `.gitignore` excludes `models/` (15GB Qwen weights — never commit), `__pycache__/`.
- Remote: `https://github.com/yd7148/TaipowerExam.git`
- Commit scope: scripts + `vlm_auto_report*.md` + `完整詳細解答-...md` + `.opencode/skills/taipower-exam-report/SKILL.md`. Files under `test-pdf/.../提取結果_v4/q*.png` are large; keep them out of commits unless asked.

## Ongoing Limits (known)

- VLM topology reading is unreliable → most questions land in `REVIEW` by design; only accept as PASS when SPICE matches official answer.
- Not yet implemented: BJT models (Q27/33/39), zener model (Q38), AC phasor sim (Q19), dual-source Vab target (Q2).
- Q1 official R_eq=4Ω is unreachable from any SP combo of {10,10,5,5} — flagged REVIEW.