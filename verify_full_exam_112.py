"""Verify the generated 113 full-answer report against the authoritative key.

Checks for every question: section header answer, 題目/答案選項/實際答案/解題過程
presence, and agreement with answers_112.json. Results saved to a separate file.
"""
import re
import json
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(BASE, '完整詳細解答- 112 年經濟部所屬事業機構新進職員甄試試題.md')
QDIR = os.path.join(BASE, 'test-pdf', '112-2023', '電機(一)', '提取結果_v112')
OUT = os.path.join(BASE, '驗證結果- 112 年經濟部所屬事業機構新進職員甄試試題.md')

with open(os.path.join(QDIR, 'answers_112.json'), encoding='utf-8') as f:
    official = {int(k): v for k, v in json.load(f).items()}

text = open(REPORT, encoding='utf-8').read()
sections = re.split(r'(?m)^## Q(\d+) —', text)

rows = []
header_mism = []
for i in range(1, len(sections), 2):
    qid = int(sections[i])
    body = sections[i + 1]
    m = re.search(r'官方答案：(.+?）)', body)
    header_ans = m.group(1).strip().rstrip('）') if m else '?'
    has_q = '**題目：**' in body
    has_o = '**答案選項：**' in body and '**實際答案：**' in body
    has_s = '**解題過程：**' in body
    off = official[qid]
    header_ok = (header_ans == off) or (header_ans.startswith(off) and off in header_ans)
    if not header_ok:
        header_mism.append((qid, header_ans, off))
    rows.append({
        'qid': qid, 'header_ans': header_ans, 'official': off,
        'question': has_q, 'options': has_o, 'solution': has_s, 'header_ok': header_ok
    })

bad = [r for r in rows if not (r['question'] and r['options'] and r['solution'] and r['header_ok'])]

lines = []
lines.append("# 驗證結果 — 112 年經濟部所屬事業機構新進職員甄試試題（完整詳細解答）")
lines.append("")
lines.append(f"- 檢查時間：今日")
lines.append(f"- 受測檔案：`{os.path.basename(REPORT)}`")
lines.append(f"- 比對基準：`answers_112.json`（官方解答 PDF 解析之答案鍵）")
lines.append(f"- 檢查項目：每一題含 ① 題目 ② 答案選項 ③ 實際答案 ④ 解題過程 ⑤ 標頭答案=官方答案")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 1. 整體結果")
lines.append("")
lines.append(f"| 項目 | 結果 |")
lines.append(f"|---|---|")
lines.append(f"| 題數 | {len(rows)} |")
lines.append(f"| 全部通過 | {'✅ 是' if not bad else '❌ 否'} |")
lines.append(f"| 未過題數 | {len(bad)} |")
lines.append("")
lines.append("## 2. 逐題檢查表")
lines.append("")
lines.append("| 題號 | 標頭答案 | 官方答案 | 題目 | 選項 | 實際答案 | 解題過程 | 標頭=官方 |")
lines.append("|---|---|---|---|---|---|---|---|")
for r in rows:
    lines.append(
        f"| {r['qid']} | {r['header_ans']} | {r['official']} | "
        f"{'✓' if r['question'] else '✗'} | {'✓' if r['options'] else '✗'} | "
        f"{'✓' if r['options'] else '✗'} | {'✓' if r['solution'] else '✗'} | "
        f"{'✓' if r['header_ok'] else '✗'} |"
    )
lines.append("")
lines.append("## 3. 失敗明細")
lines.append("")
if header_mism:
    lines.append("以下題目標頭答案與官方鍵不一致（需人工修正）：")
    lines.append("")
    for qid, ha, off in header_mism:
        lines.append(f"- Q{qid}: 標頭 {ha} ≠ 官方 {off}")
    lines.append("")
else:
    lines.append("（無）")
lines.append("")
lines.append("---")
lines.append("")
lines.append("*驗證完畢*")
lines.append("")

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"checked {len(rows)} questions, failed={len(bad)}")
if bad:
    for r in bad:
        print(f"  FAIL Q{r['qid']}: header={r['header_ans']} official={r['official']} q={r['question']} o={r['options']} s={r['solution']}")
print(f"verify report saved: {OUT}")