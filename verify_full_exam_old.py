# -*- coding: utf-8 -*-
"""Generalized verifier for old-year full-answer reports.

Usage: python verify_full_exam_old.py <year_key>
Checks each question block in the generated report for 題目/選項/實際答案/解題過程
presence and header-answer agreement with the official key.
"""
import re, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))

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


def norm(a):
    a = str(a)
    if '送分' in a:
        return '送分'
    if '或' in a:
        return a.strip()
    c = a[0] if a else ''
    return c if c.isalpha() else a


def main(year_key):
    qdir, N, title = CFG[year_key]
    year = year_key.rstrip('甲乙')
    QDIR = os.path.join(BASE, qdir)
    REPORT = os.path.join(BASE, f'完整詳細解答- {title}.md')
    OUT = os.path.join(BASE, f'驗證結果- {title}.md')

    official = {int(k): v for k, v in json.load(open(os.path.join(QDIR, f'answers_{year}.json'), encoding='utf-8')).items()}
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
        off = official.get(qid, '?')
        header_ok = norm(header_ans) == norm(off)
        if not header_ok:
            header_mism.append((qid, header_ans, off))
        rows.append(dict(qid=qid, header_ans=header_ans, official=off,
                         question=has_q, options=has_o, solution=has_s, header_ok=header_ok))

    missing = [q for q in range(1, N + 1) if q not in [r['qid'] for r in rows]]
    for q in missing:
        rows.append(dict(qid=q, header_ans='?', official=official.get(q, '?'),
                         question=False, options=False, solution=False, header_ok=False))

    bad = [r for r in rows if not (r['question'] and r['options'] and r['solution'] and r['header_ok'])]

    lines = []
    lines.append(f"# 驗證結果 — {title}（完整詳細解答）")
    lines.append("")
    lines.append(f"- 受測檔案：`{os.path.basename(REPORT)}`")
    lines.append(f"- 比對基準：`answers_{year}.json`（官方解答 PDF 解析之答案鍵）")
    lines.append("- 檢查項目：每一題含 ① 題目 ② 答案選項 ③ 實際答案 ④ 解題過程 ⑤ 標頭答案=官方答案")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. 整體結果")
    lines.append("")
    lines.append("| 項目 | 結果 |")
    lines.append("|---|---|")
    lines.append(f"| 題數 | {len(rows)} |")
    lines.append(f"| 全部通過 | {'✅ 是' if not bad else '❌ 否'} |")
    lines.append(f"| 未過題數 | {len(bad)} |")
    lines.append("")
    lines.append("## 2. 逐題檢查表")
    lines.append("")
    lines.append("| 題號 | 標頭答案 | 官方答案 | 題目 | 選項 | 實際答案 | 解題過程 | 標頭=官方 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: x['qid']):
        lines.append(
            f"| {r['qid']} | {r['header_ans']} | {r['official']} | "
            f"{'✓' if r['question'] else '✗'} | {'✓' if r['options'] else '✗'} | "
            f"{'✓' if r['options'] else '✗'} | {'✓' if r['solution'] else '✗'} | "
            f"{'✓' if r['header_ok'] else '✗'} |")
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
    for r in bad:
        print(f"  FAIL Q{r['qid']}: header={r['header_ans']} official={r['official']} "
              f"q={r['question']} o={r['options']} s={r['solution']}")
    print(f"verify report saved: {OUT}")


if __name__ == '__main__':
    for k in sys.argv[1:]:
        main(k)