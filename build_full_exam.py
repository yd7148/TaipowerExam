"""Generate the complete 50-question detailed answer document for the 114 exam.

Merges 完整解答.md (題目/選項/官方答案/解題過程 for all 50 questions)
with vlm_auto_report.json (VLM verdict for the 16 circuit-diagram questions).
Output filename follows the convention: <名称>- 114 年經濟部所屬事業機構新進職員甄試試題.md
"""
import re
import json
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
FULL = os.path.join(BASE, 'test-pdf', '114-2025', '電機', '提取結果_v4', '完整解答.md')
REPORT = os.path.join(BASE, 'vlm_auto_report.json')
OUT = os.path.join(BASE, '完整詳細解答- 114 年經濟部所屬事業機構新進職員甄試試題.md')

CIRCUIT_QUESTIONS = [1, 2, 3, 4, 17, 19, 27, 29, 32, 33, 36, 38, 39, 44, 45, 50]

# ============================================================
# Load 完整解答.md and split into per-question segments
# ============================================================
with open(FULL, encoding='utf-8') as f:
    text = f.read()

segments = re.split(r'(?m)^### 第(\d+)題 【答案：([^】]+)】', text)
qmap = {}
for i in range(1, len(segments), 3):
    qid = int(segments[i])
    ans = segments[i + 1].strip()
    body = segments[i + 2]
    qmap[qid] = {'answer': ans, 'body': body}

# Cross-check header answers with the pipeline's official answer key
PIPE_KEYS = {1:'C',2:'D',3:'C',4:'B',5:'A',6:'A',7:'B',8:'A',9:'A',10:'B',11:'D',
             12:'B',13:'C',14:'C',15:'B',16:'D',17:'C',18:'D',19:'B',20:'S',21:'C',
             22:'D',23:'B',24:'B',25:'A',26:'D',27:'B',28:'A',29:'D',30:'D',31:'C',
             32:'C',33:'D',34:'B',35:'A',36:'B',37:'D',38:'C',39:'B',40:'A',41:'A',
             42:'D',43:'A',44:'B',45:'C',46:'C',47:'D',48:'A',49:'A',50:'A'}


def extract_question(body):
    m = re.search(r'\*\*(.+?)\*\*', body)
    return m.group(1).strip() if m else ''


def extract_options(body):
    """All lines that start with (A)/(B)/(C)/(D), consecutive block."""
    opts = []
    for line in body.splitlines():
        s = line.strip()
        if re.match(r'^\([ABCD]\)', s):
            opts.append(re.sub(r'\*+$', '', s))
        elif opts and s:
            break
    return '\n'.join(opts)


def extract_elements(body):
    m = re.search(r'\*\*電路元件：\*\*(.+)', body)
    return m.group(1).strip() if m else None


def extract_solution(body):
    m = re.search(r'\*\*解題過程：\*\*\s*(.*?)$', body, re.S)
    if not m:
        return ''
    sol = m.group(1).strip()
    sol = re.split(r'\n## ', sol)[0]
    sol = re.sub(r'\n*-+\s*$', '', sol).strip()
    return sol


# ============================================================
# Load VLM results
# ============================================================
with open(REPORT, encoding='utf-8') as f:
    data = json.load(f)
results = {int(k): v for k, v in data['results'].items()}

verdict_cn = {
    'PASS': '✅ PASS',
    'REVIEW': '⚠️ REVIEW',
    'SIM-ERR': '❌ SIM-ERR',
    'NO-CIRCUIT': '無電路',
    'NO-PYSPICE': 'NO-PYSPICE',
}


def vlm_block(r):
    """Markdown block describing the VLM verdict for a circuit question."""
    verdict = r.get('verdict', '')
    lines = []
    if verdict == 'PASS':
        lines.append(f"**VLM 判讀：** {r.get('note', '')}")
        lines.append("")
        lines.append("```text")
        lines.append(r.get('netlist', ''))
        lines.append("```")
        lines.append("")
    elif verdict == 'REVIEW' and 'reason' in r:
        lines.append(f"**VLM 判讀：** {r['reason']}")
        lines.append("")
    elif verdict == 'REVIEW' and 'parts' in r:
        lines.append(f"**VLM 判讀：** 偵測到不支援元件 {', '.join(r['parts'])}")
        lines.append("")
    elif verdict == 'REVIEW' and 'symbolic' in r:
        lines.append(f"**VLM 判讀：** 符號值元件 {', '.join(r['symbolic'])} 無法模擬")
        lines.append("")
    elif verdict == 'REVIEW':
        lines.append(f"**VLM 判讀：** 需人工檢查（{r.get('note', '無具體原因')}）")
        lines.append("")
    elif verdict == 'SIM-ERR':
        lines.append(f"**VLM 判讀：** 模擬錯誤（{r.get('error', '')}）— 擷取拓撲有誤")
        lines.append("")
    if 'nodes' in r and r['nodes']:
        nodes = r['nodes']
        vals = ', '.join(f"{k}={float(v):.2f}" for k, v in sorted(nodes.items())[:8])
        lines.append(f"**模擬節點電壓：** {vals}")
        lines.append("")
    return lines


# ============================================================
# Build the document
# ============================================================
out = []
out.append("# 114 年經濟部所屬事業機構新進職員甄試試題 — 完整詳細解答")
out.append("")
out.append("> **科目 A（電機、儀電類）：1. 電路學　2. 電子學**　共 50 題")
out.append(">")
out.append("> - 題目／選項／官方答案／解題過程：取自 OCR 結果與官方解答")
out.append("> - 電路圖題目之元件判讀：`vlm_auto_pipeline.py`（Qwen2.5-VL-7B 影像→元件→SPICE→官方答案比對）")
out.append("> - 文字題目：由 LLM 解題並與官方答案核對")
out.append("")
out.append("---")
out.append("")

for qid in range(1, 51):
    q = qmap.get(qid)
    r = results.get(qid, {})
    verdict = r.get('verdict', '')
    if qid in CIRCUIT_QUESTIONS:
        tag = verdict_cn.get(verdict, verdict)
    else:
        tag = '📝 文字題'
    header_ans = q['answer'] if q else '?'
    letter = header_ans[0] if header_ans and header_ans[0] in 'ABCD' else '（送分）'
    out.append(f"## Q{qid} — {tag}（官方答案：{letter}）")
    out.append("")

    if q:
        q_text = extract_question(q['body'])
        opts = extract_options(q['body'])
        elems = extract_elements(q['body'])
        sol = extract_solution(q['body'])
        if q_text:
            out.append(f"**題目：** {q_text}")
            out.append("")
        if opts:
            out.append("**答案選項：**")
            out.append("")
            out.append(opts)
            out.append("")
        if elems:
            out.append(f"**電路元件：** {elems}")
            out.append("")

    out.append(f"**實際答案：** {letter}（官方 {header_ans}）")
    out.append("")

    if qid in CIRCUIT_QUESTIONS:
        for line in vlm_block(r):
            out.append(line)

    if q and sol:
        out.append("**解題過程：**")
        out.append("")
        out.append(sol)
        out.append("")

    out.append("---")
    out.append("")

# ============================================================
# Answer key summary table
# ============================================================
out.append("## 總結：50 題答案一覽表")
out.append("")
out.append("| 題號 | 答案 | 題號 | 答案 | 題號 | 答案 | 題號 | 答案 | 題號 | 答案 |")
out.append("|---|---|---|---|---|---|---|---|---|---|")
for row in range(0, 10):
    cells = []
    for col in range(0, 5):
        qid = row + col * 10 + 1
        letter = qmap[qid]['answer'] if qid in qmap else '?'
        if letter.startswith('一') or letter == '送分':
            letter = '送分'
        else:
            letter = letter[0]
        cells.append(f"{qid} | {letter}")
    out.append("| " + " | ".join(cells) + " |")
out.append("")
out.append("---")
out.append("")
out.append("*資料來源：台灣電力公司 114 年度新進職員甄試試題解答 A_電機_電路學電子學*")
out.append("")

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print(f"generated {OUT}")
for qid in range(1, 51):
    r = results.get(qid, {})
    tag = verdict_cn.get(r.get('verdict', ''), r.get('verdict', '')) if qid in CIRCUIT_QUESTIONS else '文字題'
    ok = 'ok' if qid in qmap else 'MISSING'
    print(f"  Q{qid:2d}: {tag:14s} {ok}")

# answer-key cross check
mism = [qid for qid in range(1, 51) if qid in qmap and qmap[qid]['answer'].startswith(('A', 'B', 'C', 'D')) and qmap[qid]['answer'][0] != PIPE_KEYS.get(qid)]
print("answer cross-check mismatches:", mism if mism else "NONE")