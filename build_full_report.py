"""Merge 完整解答.md question blocks + vlm_auto_report.json into a full markdown report."""
import re
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
FULL = os.path.join(BASE, 'test-pdf', '114-2025', '電機', '提取結果_v4', '完整解答.md')
REPORT = os.path.join(BASE, 'vlm_auto_report.json')
OUT = os.path.join(BASE, 'vlm_auto_report_full.md')

with open(FULL, encoding='utf-8') as f:
    text = f.read()

# Split into per-question segments
segments = re.split(r'(?m)^### 第(\d+)題 【答案：([^】]+)】', text)
qmap = {}
for i in range(1, len(segments), 3):
    qid = int(segments[i])
    ans = segments[i + 1].strip()
    body = segments[i + 2]
    qmap[qid] = {'answer': ans, 'body': body}

def extract_question(body):
    m = re.search(r'\*\*(.+?)\*\*', body)
    return m.group(1).strip() if m else ''

def extract_options(body):
    for line in body.splitlines():
        line = line.strip()
        if line.startswith('(A)') and '(B)' in line:
            # strip any trailing "**" artifacts
            return re.sub(r'\*+$', '', line)
    return ''

def extract_elements(body):
    m = re.search(r'\*\*電路元件：\*\*(.+)', body)
    return m.group(1).strip() if m else None

def extract_solution(body):
    m = re.search(r'\*\*解題過程：\*\*\s*(.*?)$', body, re.S)
    if not m:
        return ''
    sol = m.group(1).strip()
    # cut at the first '## ' section heading (e.g. 總結), keep only the solution
    sol = re.split(r'\n## ', sol)[0]
    # strip trailing markdown separators
    sol = re.sub(r'\n*-+\s*$', '', sol).strip()
    return sol

def extract_verified(body):
    m = re.search(r'\*\*驗證[：:]\*\*(.*)', body)
    return m.group(1).strip() if m else None

with open(REPORT, encoding='utf-8') as f:
    data = json.load(f)
results = {int(k): v for k, v in data['results'].items()}

CIRCUIT_QUESTIONS = [1, 2, 3, 4, 17, 19, 27, 29, 32, 33, 36, 38, 39, 44, 45, 50]

out = []
out.append("# 台電招考 電路學 VLM 自動判讀完整報告")
out.append("")
out.append("> 題目／選項／官方答案／解題過程：取自 114 年經濟部所屬事業機構新進職員甄試試題")
out.append("> VLM 判讀：`vlm_auto_pipeline.py` 自動模式（影像→元件→答案反推→SPICE→比對）")
out.append("")

verdict_cn = {
    'PASS': '✅ PASS',
    'REVIEW': '⚠️ REVIEW',
    'SIM-ERR': '❌ SIM-ERR',
    'NO-CIRCUIT': '無電路',
    'NO-PYSPICE': 'NO-PYSPICE',
}

for qid in CIRCUIT_QUESTIONS:
    q = qmap.get(qid)
    r = results.get(qid, {})
    verdict = r.get('verdict', '')
    official_letter = q['answer'][0] if q and q['answer'] and q['answer'][0] in 'ABCD' else r.get('official_letter', '')
    out.append(f"## Q{qid} — {verdict_cn.get(verdict, verdict)}（官方答案：{official_letter}）")
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
            out.append(f"**答案選項：**\n\n{opts}")
            out.append("")
        if elems:
            out.append(f"**電路元件：** {elems}")
            out.append("")
    out.append(f"**實際答案：** {official_letter}（官方 {q['answer'] if q else '?'}）")
    out.append("")
    # VLM verdict detail
    if verdict == 'PASS':
        out.append(f"**VLM 判讀：** {r.get('note', '')}")
        out.append("")
        out.append("```")
        out.append(r.get('netlist', ''))
        out.append("```")
        out.append("")
    elif verdict == 'REVIEW' and 'reason' in r:
        out.append(f"**VLM 判讀：** {r['reason']}")
        out.append("")
    elif verdict == 'REVIEW' and 'parts' in r:
        out.append(f"**VLM 判讀：** 偵測到不支援元件 {', '.join(r['parts'])}")
        out.append("")
    elif verdict == 'REVIEW' and 'symbolic' in r:
        out.append(f"**VLM 判讀：** 符號值元件 {', '.join(r['symbolic'])} 無法模擬")
        out.append("")
    elif verdict == 'REVIEW':
        out.append(f"**VLM 判讀：** 需人工檢查（{r.get('note', '無具體原因')}）")
        out.append("")
    elif verdict == 'SIM-ERR':
        out.append(f"**VLM 判讀：** 模擬錯誤（{r.get('error', '')}）— 擷取拓撲有誤")
        out.append("")
    if 'nodes' in r and r['nodes']:
        nodes = r['nodes']
        vals = ', '.join(f"{k}={float(v):.2f}" for k, v in sorted(nodes.items())[:8])
        out.append(f"**模擬節點電壓：** {vals}")
        out.append("")
    # Solution process
    sol = extract_solution(q['body']) if q else ''
    if sol:
        out.append("**解題過程：**")
        out.append("")
        out.append(sol)
        out.append("")
    out.append("---")
    out.append("")

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print(f"generated {OUT} with {len(CIRCUIT_QUESTIONS)} questions")
for qid in CIRCUIT_QUESTIONS:
    r = results.get(qid, {})
    print(f"  Q{qid}: {r.get('verdict','?'):12s} question={'yes' if qid in qmap else 'NO'}")