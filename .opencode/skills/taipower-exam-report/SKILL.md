---
name: taipower-exam-report
description: Use when the user asks to generate a complete detailed answer report (整份考題詳細解答) for 國營事業/台電 exam PDFs from OCR-extracted questions, or build 電路學/電子學 circuit-diagram solutions from VLM component extraction + SPICE simulation + official answer matching. Covers the Qwen2.5-VL-7B pipeline (vlm_auto_pipeline_YYY.py), SP topology back-inference (resistor_sp.py), the markdown report generators (build_full_exam_YYY.py), and the verifiers (verify_full_exam_YYY.py). Multiple years supported (110/111/112/113, plus 114 in progress). Use for naming report files "*- NN 年經濟部所屬事業機構新進職員甄試試題.md" and syncing to GitHub.
---

# Taipower Exam Report

End-to-end workflow: OCR-extracted exam questions → (for circuit diagrams) Qwen2.5-VL-7B component extraction → SP topologies back-inferred from values + official answer → ngspice/PySpice simulation → verdict (PASS/REVIEW/SIM-ERR) → merge with per-question authoritative content into a complete detailed-answer markdown report.

## Year Matrix (110 / 111 / 112 / 113 電機(一); 114 in progress)

| Item | 110 | 111 | 112 | 113 |
|---|---|---|---|---|
| Folder | `test-pdf/110-2021/電機(一)/` | `test-pdf/111-2022/電機(一)/` | `test-pdf/112-2023/電機(一)/` | `test-pdf/113-2024/電機/` |
| Extraction dir | `提取結果_v110/` | `提取結果_v111/` | `提取結果_v112/` | `提取結果_v113/` |
| Official key | `answers_110.json` | `answers_111.json` | `answers_112.json` | `answers_113.json` |
| VLM pipeline | `vlm_auto_pipeline_110.py` | `vlm_auto_pipeline_111.py` | `vlm_auto_pipeline_112.py` | `vlm_auto_pipeline_113.py` |
| VLM report | `vlm_auto_report_110.json` | `vlm_auto_report_111.json` | `vlm_auto_report_112.json` | `vlm_auto_report_113.json` |
| Report builder | `build_full_exam_110.py` | `build_full_exam_111.py` | `build_full_exam_112.py` | `build_full_exam_113.py` |
| Verifier | `verify_full_exam_110.py` | `verify_full_exam_111.py` | `verify_full_exam_112.py` | `verify_full_exam_113.py` |
| Circuit Qs (count) | 19 | 30 | 18 | 19 |

Circuit question lists:
- 110: `[6,7,9,10,11,12,18,24,30,31,39,40,41,42,46,47,48,49,50]`
- 111: `[2,3,4,7,8,9,11,12,13,14,16,19,22,25,27,28,29,30,33,34,38,40,42,43,44,45,46,48,49,50]`
- 112: `[1,2,3,5,6,7,8,9,10,11,15,16,18,20,22,24,25,29]`
- 113: `[4,5,6,9,10,12,17,18,21,22,23,28,31,36,38,40,42,45,50]`

All four years are **complete** (答案 cross-check NONE, verify 50/50 failed=0). 114 is WIP.

## Directory Layout

```
test-pdf/<YY>-<year>/電機(一)/提取結果_v<YY>/      (YY=110..113; 113 uses 電機/ without 科別)
  q01.png ... q50.png      # per-question cropped images (full-width rows, ZOOM=2, includes right-side diagram)
  q01.md  ... q50.md       # per-question OCR text / authoritative parsed content
  answers_<YY>.json        # per-year official answer key
  exam_pageN.png / answer_pageN.png
```

## Key Scripts (project root E:\01-Project\2026-08-Taipower-test)

- `extract_<YYY>.py` (in `C:\Users\4pins\AppData\Local\Temp\opencode\` for 111/110; on disk for 112/113) — PDF question/answer parsing + per-question crop via pdfplumber qpos. Generates `q??.md` + `q??.png` + `answers_<YYY>.json`.
- `vlm_auto_pipeline_<YYY>.py` — VLM auto pipeline: image → components → SP back-inference → SPICE → verdict. Generated per year by copying the newest and swapping `IMAGE_BASE`, `CIRCUIT_QUESTIONS`, `ANSWER_LETTERS` (=`answers_<YYY>.json`), `ANSWER_VALUES`, and report path `vlm_auto_report_<YYY>.json`.
  - Long tasks (≥~12 circuit Qs, e.g. 110/111) are run in **part1/part2** subsets then merged into the final report; restore the script to full list afterwards.
  - `resistor_sp.py` back-inference is wired in via `_back_infer`.
  - VLM = `Qwen2_5_VLForConditionalGeneration` (NOT AutoModelForVision2Seq), `max_new_tokens=900, do_sample=False`, image resized to 600px width, device_map='cuda:0'.
- `resistor_sp.py` — brute-force series/parallel topology search using `Fraction`; `test_sp.py` validates it (all pass).
- `build_full_exam_<YYY>.py` — merge *all 50 questions* (題目/選項/實際答案/解題過程 + VLM verdict for circuit Qs).
  - Reads q??.md headers as authoritative answers and embeds a freshly-written `SOLUTIONS` dict; it does **not** trust old 完整解答.md.
  - Holds an `OPTION_REPAIR` dict for damaged option text (e.g. 110 Q40 `Vout Vs` → `Vout/Vs`). md fixes are edited in-place; repair dict can stay empty if md is already clean.
  - Output: **`完整詳細解答- <NN> 年經濟部所屬事業機構新進職員甄試試題.md`**.
- `verify_full_exam_<YYY>.py` — parses the generated report and checks every question: 題目/選項/實際答案/解題過程 present AND header answer == `answers_<YYY>.json`. Writes **`驗證結果- <NN> 年...md`** (separate file per user request).
- `exam_agent.py` — main solver agent (SymPy/MNA/PySpice triple verification).

## Extraction Gotchas (per-year, from 110/111/112/113)

- **答案標記正則**: official answer PDF uses `[X] N.` for single letters but **year-specific composite** keys exist — e.g. 110 Q43 = `A或C` (複選/送分). Use `\[([A-Ea-e]|A或C|B或D|A和C|B和D|\w+或\w+)\]` so composite keys are captured; report/verify must handle `A或C` (match when header starts with the composite key).
- **選項跨行**: option text may split across lines (110 Q40 `(D)\nVout\nVs ...`). Add a "空選項併入後續行" patch so the empty option line is folded into the following line.
- **答案檔名**: when copying an extract script from another year, verify the `answers_XXXX.json` path points at the CURRENT year (110 copy had stale `answers_111.json`).
- **Q34-style 撞名**: the question body can contain `(B)端` alongside real options (110 Q34); the option parser can mis-split. Fix the q??.md by moving the stray text back into the question line and restoring the real option.
- Rule of thumb: always spot-check a handful of q??.md (especially damaged-looking ones) before building.

## 110-Specific Notes

- 110 Q43 official answer is **`A或C`** (複選/送分) — build displays it as `A或C（複選/送分）`, verify matches by prefix.
- Hand-fixed in q34.md (stray `(B)` absorbed into question) and q15/q18/q22/q25/q42 for 111 analog work.
- Answers key (50 Qs): `1D 2B 3A 4D 5B 6D 7D 8C 9A 10C 11C 12D 13C 14B 15A 16A 17B 18B 19C 20A 21C 22A 23C 24A 25D 26D 27A 28C 29C 30A 31C 32B 33A 34B 35B 36D 37C 38B 39C 40D 41B 42C 43=A或C 44B 45A 46B 47D 48A 49A 50D`.

## 111-Specific Notes

Damaged-file repairs (edit q??.md, verify via repr — `?` may be console-only display artifact):
- Q6 D: `£[df(t)/dt] = sF(s)` → correct is `sF(s) − f(0⁻)`.
- Q15: trailing Q8 diagram labels bled in — removed.
- Q18: options are `(A)½Cv(t) (C)½Li(t) (D)½Li²(t)`.
- Q22: question+options rebuilt (answer C: `44/3 sin(120πt−45°) A`).
- Q25 D: `Z22 = 4s + 1/(3s)`.
- Q42: options rebuilt (answer A: `Y=ĀB＋AB̄`).

## 112-Specific Notes

When the official key conflicts with a formula (e.g. Q12), the **official key wins** and the report annotates the discrepancy (established precedent).

## 113-Specific Lessons (9 previously-mistaken answers)

Old 完整解答.md headers contradicted official key on Q3/Q4/Q11/Q21/Q22/Q24/Q28/Q33/Q34 and sometimes rewrote correct math to force the wrong option. Correct as of the official key:
- Q3 = B (4A): R=ρL/A=2Ω, I=8/2=4A. (old forced C)
- Q4 = A (0A): balanced Wheatstone bridge 4/8 = 5/10 → I=0.
- Q11 = A: numerator is `15S²+56S+47`, Heaviside residues → 3e⁻ᵗ+5e⁻²ᵗ+7e⁻³ᵗ.
- Q21 = B (1+√3), Q22 = A (1.5Ω), Q24 = D (6Hz: f0=1/(2π√(LC))), Q33 = D (12.5Ω), Q34 = D (15.7V Vp-p).
- Q28 = official composite **A、C** (複選/送分) — report IC=1.96mA (C) then note both accepted.
- Always regenerate solutions from the official answer PDF text, never reuse old 完整解答.md conclusions verbatim.

## Environment Gotchas (Windows)

- Output: wrap with `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')` before printing Chinese/emoji.
- Import torch BEFORE HF/PySpice imports; set `KMP_DUPLICATE_LIB_OK='TRUE'` first.
- PySpice: `os.add_dll_directory(r'C:\ngspice\Spice64_dll\dll-vs')` + `r'C:\ngspice\Spice64\bin'`.
- **Never** call `ngspice -b x.cir` directly — it hangs after ~60s; always use PySpice `circuit.simulator()` (the `CircuitSimulator(circ)` class is deprecated, no `.SIMULATOR` attr).
- Branch keys are prefixed, e.g. source `V1` → branch `vv1`; use `str(key).endswith('v1')` to find it.
- Full-width punctuation: regex against report must use `（`/`）` not `(`/`)`.
- List/extract under UTF-8; PowerShell console often shows Chinese as mojibake — read files via the Read tool, not console, to verify content.

## Report Naming Convention

`.md` files on GitHub must follow: `<short description>- <NN> 年經濟部所屬事業機構新進職員甄試試題.md`
(e.g. `完整詳細解答- 110 年經濟部所屬事業機構新進職員甄試試題.md`, `驗證結果- 110 年經濟部所屬事業機構新進職員甄試試題.md`).

## GitHub Sync

- `.gitignore` excludes `models/` (15GB Qwen weights — never commit), `__pycache__/`.
- Remote: `https://github.com/yd7148/TaipowerExam.git`
- Commit scope: scripts + `vlm_auto_report*.json` + `完整詳細解答-...md` + `驗證結果-...md` + `.opencode/skills/taipower-exam-report/SKILL.md`. Files under `test-pdf/.../提取結果_v*/q*.png` are large; keep them out of commits unless asked.

## Ongoing Limits (known)

- VLM topology reading is unreliable → most questions land in `REVIEW`/`NO-CIRCUIT` by design; only accept as PASS when SPICE matches official answer.
- 113 crops are short full-width rows; Q21/Q22 (infinite-ladder / small diagrams) come back NO-CIRCUIT — fine, that's a documented verdict not a failure.
- Not yet implemented: BJT models, zener model, AC phasor sim, multi-valued unlabeled questions.