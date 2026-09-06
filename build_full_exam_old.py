# -*- coding: utf-8 -*-
"""Generalized full-answer report builder for old Taipower exam years.

Usage: python build_full_exam_old.py <year_key>
year_key in the CFG below (e.g. '108', '106甲', ...).

Reads per-question content from 提取結果_*/q??.md (題目/選項/官方答案),
VLM verdicts from vlm_auto_report_<year>.json, and freshly written solutions
from solutions_<year_key>.json (qid -> markdown/LaTeX text). Emits the
完整詳細解答- <title>.md report and cross-checks answers against the key.
"""
import re, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))

# year_key: (extract_dir, out_suffix, n_questions, report_title)
CFG = {
    '108':  (r'test-pdf\108-2019\電機\提取結果_v108', 50,
             '108 年經濟部所屬事業機構新進職員甄試試題'),
    '107':  (r'test-pdf\107-2018\電機\提取結果_v107', 50,
             '107 年經濟部所屬事業機構新進職員甄試試題'),
    '106甲': (r'test-pdf\106-2017\電機(甲)\提取結果_v106a', 50,
              '106 年經濟部所屬事業機構新進職員甄試試題（電機(甲)）'),
    '106乙': (r'test-pdf\106-2017\電機(乙)\提取結果_v106b', 50,
              '106 年經濟部所屬事業機構新進職員甄試試題（電機(乙)）'),
    '105甲': (r'test-pdf\105-2016\電機(甲)\提取結果_v105a', 50,
              '105 年經濟部所屬事業機構新進職員甄試試題（電機(甲)）'),
    '105乙': (r'test-pdf\105-2016\電機(乙)\提取結果_v105b', 50,
              '105 年經濟部所屬事業機構新進職員甄試試題（電機(乙)）'),
    '104甲': (r'test-pdf\104-2015\電機(甲)\提取結果_v104a', 50,
              '104 年經濟部所屬事業機構新進職員甄試試題（電機(甲)）'),
    '104乙': (r'test-pdf\104-2015\電機(乙)\提取結果_v104b', 50,
              '104 年經濟部所屬事業機構新進職員甄試試題（電機(乙)）'),
    '103乙': (r'test-pdf\103-2014\電機(乙)\提取結果_v103b', 40,
              '103 年經濟部所屬事業機構新進職員甄試試題（電機(乙)）'),
}

verdict_cn = {
    'PASS': '✅ PASS', 'REVIEW': '⚠️ REVIEW', 'SIM-ERR': '❌ SIM-ERR',
    'NO-CIRCUIT': '無電路', 'NO-PYSPICE': 'NO-PYSPICE',
}


def vlm_block(r):
    lines = []
    verdict = r.get('verdict', '')
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
        lines.append(f"**VLM 判讀：** 偵測到不支援元件 {', '.join(r['parts'])}（人工/公式解）")
        lines.append("")
    elif verdict == 'REVIEW' and 'symbolic' in r:
        lines.append(f"**VLM 判讀：** 符號值元件 {', '.join(r['symbolic'])} 無法模擬（人工/公式解）")
        lines.append("")
    elif verdict == 'REVIEW':
        lines.append(f"**VLM 判讀：** 需人工檢查（{r.get('note', '無具體原因')}）")
        lines.append("")
    elif verdict == 'SIM-ERR':
        lines.append(f"**VLM 判讀：** 模擬錯誤（{r.get('error', '')}）— 擷取拓撲有誤，採人工/公式解")
        lines.append("")
    elif verdict == 'NO-CIRCUIT':
        lines.append("**VLM 判讀：** 圖像過窄，VLM 未能辨識電路元件；採人工/公式解")
        lines.append("")
    if r.get('nodes'):
        n = r['nodes']
        vals = ', '.join(f"{k}={float(v):.2f}" for k, v in sorted(n.items())[:8])
        lines.append(f"**模擬節點電壓：** {vals}")
        lines.append("")
    return lines


def main(year_key):
    qdir, N, title = CFG[year_key]
    QDIR = os.path.join(BASE, qdir)
    year = year_key.rstrip('甲乙')
    _REP_CAND = (f'vlm_auto_report_{year_key}.json', f'vlm_auto_report_{year}.json')
    REPORT = next((os.path.join(BASE, c) for c in _REP_CAND if os.path.exists(os.path.join(BASE, c))),
                  os.path.join(BASE, _REP_CAND[0]))
    SOL = os.path.join(BASE, f'solutions_{year_key}.json')
    OUT = os.path.join(BASE, f'完整詳細解答- {title}.md')

    # ---- load q??.md content ----
    qmap = {}
    for qid in range(1, N + 1):
        p = os.path.join(QDIR, f'q{qid:02d}.md')
        if not os.path.exists(p):
            continue
        lines = open(p, encoding='utf-8').read().splitlines()
        ans = ''
        m = re.match(r'### 第\d+題 【答案：(.+?)】', lines[0])
        if m:
            ans = m.group(1).strip()
        body = lines[1:]
        qt, opts = [], []
        for ln in body:
            s = ln.strip()
            if not s:
                continue
            if re.match(r'^\(\s*[ABCD]\s*\)', s):
                opts.append(s)
            else:
                s = re.sub(r'^\d+[\.、]?\s*', '', s)
                qt.append(s)
        qmap[qid] = {'answer': ans, 'question': ' '.join(qt), 'options': opts}

    # ---- VLM + solutions ----
    results = {}
    if os.path.exists(REPORT):
        results = {int(k): v for k, v in json.load(open(REPORT, encoding='utf-8'))['results'].items()}
    sols = {}
    if os.path.exists(SOL):
        sols = {int(k): v for k, v in json.load(open(SOL, encoding='utf-8'))['results'].items()}

    def norm_header(a):
        a = str(a)
        if '送分' in a:
            return '送分（一律送分）'
        if '或' in a:
            return a.strip()
        c = a[0]
        return c if c in 'ABCDE' else (a or '?')

    out = []
    out.append(f"# {title} — 完整詳細解答")
    out.append("")
    if '電機(乙)' in title:
        out.append("> **科目 A（電機(乙)、資訊類）：1. 計算機概論　2. 電子學**")
    else:
        out.append("> **科目 A（電機(甲)／電機、儀電／電機類）：1. 電路學　2. 電子學**")
    out.append(f"> 共 {N} 題")
    out.append(">")
    out.append(f"> - 題目／選項／官方答案：取自官方解答 PDF（已由 `scripts_extract_old/extract_old.py` 解析）")
    out.append(f"> - 電路圖題目之元件判讀：`vlm_auto_run.py --cfg {year_key}`（Qwen2.5-VL-7B 影像→元件→SPICE→官方答案比對）")
    out.append("> - 解題過程：以官方答案為準撰寫，文字題為公式推導；電路圖題目因圖面無法以文字直接讀取，採步驟式解法")
    out.append("")
    out.append("---")
    out.append("")

    circ_ids = set(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               f'vlm_cfg_{year_key}.json'), encoding='utf-8'))['circuit_questions']) \
        if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'vlm_cfg_{year_key}.json')) else set()

    for qid in range(1, N + 1):
        q = qmap.get(qid)
        r = results.get(qid, {})
        v = r.get('verdict', '')
        tag = verdict_cn.get(v, v) if qid in circ_ids else '📝 文字題'
        letter = norm_header(q['answer']) if q else '?'
        out.append(f"## Q{qid} — {tag}（官方答案：{q['answer'] if q else '?'}）")
        out.append("")
        if q:
            if q['question']:
                out.append(f"**題目：** {q['question']}")
                out.append("")
            if q['options']:
                out.append("**答案選項：**")
                out.append("")
                out.append('\n'.join(q['options']))
                out.append("")
        out.append(f"**實際答案：** {letter}（官方 {q['answer'] if q else '?'}）")
        out.append("")
        if qid in circ_ids:
            out.extend(vlm_block(r))
        sol = sols.get(qid, '')
        if sol:
            out.append("**解題過程：**")
            out.append("")
            out.append(sol.strip())
            out.append("")
        out.append("---")
        out.append("")

    # answer summary table
    out.append(f"## 總結：{N} 題答案一覽表")
    out.append("")
    out.append("| 題號 | 答案 | 題號 | 答案 | 題號 | 答案 | 題號 | 答案 | 題號 | 答案 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    ncols = 5
    nrows = -(-N // ncols)
    for row in range(nrows):
        cells = []
        for col in range(ncols):
            qid = row + col * nrows + 1
            if qid > N:
                if cells:
                    cells.append('')
                    cells.append('')
                continue
            ans = qmap[qid]['answer'] if qid in qmap else '?'
            cells += [str(qid), str(ans)]
        out.append("| " + " | ".join(cells) + " |")
    out.append("")
    out.append("---")
    out.append("")
    out.append("*資料來源：台灣電力公司年度新進職員甄試試題解答*")
    out.append("")

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))

    # answer cross-check
    aj = json.load(open(os.path.join(QDIR, f'answers_{year}.json'), encoding='utf-8'))
    official = {int(k): v for k, v in aj.items()}
    mism = []
    for qid in range(1, N + 1):
        if qid not in qmap or qid not in official:
            mism.append(qid)
            continue
        def norm(a):
            a = str(a)
            if '送分' in a:
                return '送分'
            if '或' in a:
                return a.strip()
            return a[0] if a[:1].isalpha() else a
        if norm(qmap[qid]['answer']) != norm(official[qid]):
            mism.append(qid)
    print(f"generated {OUT}")
    print(f"answer cross-check mismatches: {mism if mism else 'NONE'}")

    prompt_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'builder_shown_{year_key}.json')
    _ = prompt_out


if __name__ == '__main__':
    for k in sys.argv[1:]:
        main(k)