# -*- coding: utf-8 -*-
"""Generalized extractor for old Taipower exam years (109..103).
Handles score-prefixed answer markers (`3 [D] 1.` and `3 [D] \n1.`), plain
`[D] 1.`, `[一律給分]`, and crops per-question images from the exam PDF.
Usage: python extract_old.py <year_key>
year_key in CFG (e.g. '109', '103甲').
"""
import io, sys, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf as fitz
import pdfplumber
import PIL.Image as PILImage

BASE = r'E:\01-Project\2026-08-Taipower-test\test-pdf'

# year_key: (exam_pdf, ans_pdf, out_suffix, n_questions)
CFG = {
    '109': (r'109-2020\電機\109年度新進職員甄試試題科目A_電機_電路學、電子學.pdf',
            r'109-2020\電機\109年度新進職員甄試試題解答A_電機_電路學、電子學.pdf', 'v109', 50),
    '108': (r'108-2019\電機\108年新進職員甄試試題科目A_電機_電路學、電子學.pdf',
            r'108-2019\電機\108年新進職員甄試試題解答A_電機_電路學、電子學.pdf', 'v108', 50),
    '107': (r'107-2018\電機\107年新進職員甄試試題科目A_電機_電路學、電子學.pdf',
            r'107-2018\電機\107年新進職員甄試試題解答A_電機_電路學、電子學.pdf', 'v107', 50),
    '106甲': (r'106-2017\電機(甲)\106年新進職員甄試試題科目A_電機(甲)_電路學、電子學.pdf',
              r'106-2017\電機(甲)\106年新進職員甄試解答科目A_電機(甲)_電路學、電子學.pdf', 'v106a', 50),
    '106乙': (r'106-2017\電機(乙)\106年新進職員甄試試題科目A_電機(乙)_計算機概論、電子學.pdf',
              r'106-2017\電機(乙)\106年新進職員甄試解答科目A_電機(乙)_計算機概論、電子學.pdf', 'v106b', 50),
    '105甲': (r'105-2016\電機(甲)\105年新進職員甄試試題科目A_16.電機(甲)_電路學、電子學.pdf',
              r'105-2016\電機(甲)\105年新進職員甄試解答科目A_16.電機(甲)_電路學、電子學.pdf', 'v105a', 50),
    '105乙': (r'105-2016\電機(乙)\105年新進職員甄試試題科目A_17.電機(乙)_計算機概論、電子學.pdf',
              r'105-2016\電機(乙)\105年新進職員甄試解答科目A_17.電機(乙)_計算機概論、電子學.pdf', 'v105b', 50),
    '104甲': (r'104-2015\電機(甲)\104年新進職員甄試試題科目A_14.電機(甲)_電路學、電子學.pdf',
              r'104-2015\電機(甲)\104年新進職員甄試解答科目A_14.電機(甲)_電路學、電子學.pdf', 'v104a', 50),
    '104乙': (r'104-2015\電機(乙)\104年新進職員甄試試題科目A_15.電機(乙)_計算機概論、電子學.pdf',
              r'104-2015\電機(乙)\104年新進職員甄試解答科目A_15.電機(乙)_計算機概論、電子學.pdf', 'v104b', 50),
    '103甲': (r'103-2014\電機(甲)\103年新進職員甄試試題科目A_13.電機(甲)_電路學、電子學.pdf',
              r'103-2014\電機(甲)\103年新進職員甄試解答科目A_13.電機(甲)_電路學、電子學.pdf', 'v103a', 40),
    '103乙': (r'103-2014\電機(乙)\103年新進職員甄試試題科目A_14.電機(乙)_計算機概論、電子學.pdf',
              r'103-2014\電機(乙)\103年新進職員甄試解答科目A_14.電機(乙)_計算機概論、電子學.pdf', 'v103b', 40),
}

ANS_CH = r'[A-Ea-e]'
ANS_MULTI = r'[A-Ea-e](?:[或] [？的]|[或][A-Ea-e])*'
SPECIAL = r'一[律律][給送][分]|一[律律]\s*\n*\s*[給送][分]|一律送分|一律給分'
ANS_PAT = '(?:' + ANS_CH + r'|[A-Ea-e]或[A-Ea-e]|一律給分)'

PAGEJUNK = re.compile(
    r'【請翻頁繼續作答】|【請另頁繼續作答】|【請繼續作答】|'
    r'(1\.)?\s*電[路路]學\s*2\.\s*電子學\s*第\s*\d+\s*頁|'
    r'計算機概[論論]、電子學\s*第\s*\d+\s*頁|'
    r'第\s*\d+\s*頁，共\s*\d+\s*頁|第\s*\d+\s*頁\s*共\s*\d+\s*頁|'
    r'新進職員甄試(試題|解答)|類\s*別[:：]|科目[:：]|節次[:：]|注意事項|本試題共|'
    r'可使用本甄試簡章\d*\.|本試題為單選題|請就各題選項中|本試題採雙面印刷|'
    r'考試結束前|考試時間[:：]|經濟部所屬事業機構'
)


def split_opts(text):
    """Split a line that may contain multiple (A)(B)(C)(D) options."""
    parts = re.split(r'(?:^|(?=\s*\(\s*[A-D]\s*\)))', text)
    return [x.strip() for x in parts if x.strip()]


def normalize_text(raw):
    return re.sub(r'\s+', ' ', raw).strip()


def main(year_key):
    exam_p, ans_p, suffix, nq = CFG[year_key]
    year = year_key.rstrip('甲乙')
    EXAM = os.path.join(BASE, exam_p)
    ANS = os.path.join(BASE, ans_p)
    OUT = os.path.join(os.path.dirname(EXAM), f'提取結果_{suffix}')
    os.makedirs(OUT, exist_ok=True)
    SCALE = 2.0
    print(f"== {year_key}: {os.path.basename(EXAM)}")

    # ---------- parse answers + question text from ANSWER PDF ----------
    full = ''
    doc = fitz.open(ANS)
    for p in doc:
        full += p.get_text()
    doc.close()

    # normalize special markers that span newlines
    full = re.sub(r'\[一[律律]\s*\n+\s*[給送]\s*\n*\s*[分]\]', '[一律給分]', full)
    full = re.sub(r'\[[一]?[律律]?\s*一律?[給送]?[分]?\]', '[一律給分]', full)

    lines = full.splitlines()
    blocks = []   # list of (ans_letter_or_special, block_text_lines, qn_or_None)
    cur_ans = None
    cur_lines = []
    cur_qn = None
    ans_seq = []  # sequential markers for cross-check

    def flush():
        nonlocal cur_ans, cur_lines, cur_qn
        if cur_ans is not None:
            blocks.append((cur_ans, cur_lines, cur_qn))
        cur_ans = None
        cur_lines = []
        cur_qn = None

    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if PAGEJUNK.search(s) and len(s) < 45:
            continue
        # try to match a marker: [X] or score [X]
        m = re.match(r'^(\d{1,2})\s*\[(' + ANS_PAT + r')\]\s*(.*)$', s)
        m2 = re.match(r'^\[(' + ANS_PAT + r')\]\s*(.*)$', s)
        if m or m2:
            flush()
            if m:
                cur_ans = m.group(2)
                r = m.group(3).strip()
            else:
                cur_ans = m2.group(1)
                r = m2.group(2).strip()
            ans_seq.append(cur_ans)
            # some years put the question number inline right after the marker
            # (e.g. `10有關於...` without a separator) -> capture it here
            qm = re.match(r'^(?:(\d{1,2})(?:[、.．]\s*|\s*))(.*)$', r)
            if qm:
                cur_qn = int(qm.group(1))
                r = qm.group(2).strip()
            if r:
                cur_lines.extend(split_opts(r))
            continue
        if cur_ans is not None:
            cur_lines.append(s)
    flush()

    # assign question numbers: prefer marker-scraped qn, else scan block text
    entries = {}   # qn -> {answer, text}
    for ans, blines, mqn in blocks:
        qn = mqn
        if qn is not None:
            # strip the leading question-number token from the first line
            if blines:
                f = blines[0]
                fm = re.match(r'^' + str(qn) + r'[、.．]?\s*(.*)$', f)
                if fm:
                    blines[0] = fm.group(1)
        for b in blines:
            if qn is not None:
                break
            mm = re.match(r'^(\d{1,2})[、.．]\s*(.*)$', b)
            if mm:
                qn = int(mm.group(1))
                rest = mm.group(2).strip()
                # replace this line with the rest (question text after number)
                blines = [rest] + [x for x in blines if x is not b]
                break
            # some formats put qnum alone like "33. " or the qnum is inline
            mm2 = re.match(r'^(\d{1,2})\s*[、.．]?$', b)
            if mm2:
                qn = int(mm2.group(1))
                blines = [x for x in blines if x is not b]
                break
        if qn is not None:
            ans_disp = '送分' if ans == '一律給分' else ans.upper()
            entries[qn] = {'answer': ans_disp, 'text': blines}

    # build per-question head/options
    def clean_tail(t):
        t = PAGEJUNK.sub(' ', t)
        return re.sub(r'\s{2,}', ' ', t).strip()

    ann = {}
    for qn in range(1, nq + 1):
        e = entries.get(qn)
        if not e:
            continue
        head = []
        opts = {}
        blines = e['text']
        # expand lines that carry multiple inline options
        expanded = []
        for b in blines:
            bb = b.strip()
            if not bb:
                continue
            sp = split_opts(bb)
            expanded.extend(sp)
        blines = [x for x in expanded]
        for i, b in enumerate(blines):
            b = b.strip()
            if not b:
                continue
            m = re.match(r'^\(\s*([A-D])\s*\)\s*(.*)$', b)
            if m and m.group(1) not in opts:
                val = m.group(2).strip()
                if not val:
                    j = i + 1
                    while j < len(blines):
                        nxt = blines[j].strip()
                        nm = re.match(r'^\(\s*([A-D])\s*\)', nxt)
                        if nxt and nm:
                            break
                        if nxt and not re.match(r'^[A-D]\.|^\d+[、.．]', nxt):
                            val = (val + ' ' + nxt).strip()
                            blines[j] = ''
                        j += 1
                opts[m.group(1)] = val
            else:
                head.append(b)
        qtext = clean_tail(' '.join(head))
        opts_list = [opts.get(ch, '') for ch in 'ABCD']
        ann[qn] = {'answer': e['answer'], 'question': qtext, 'options': opts_list}

    # write qNN.md
    for qn in range(1, nq + 1):
        e = ann.get(qn)
        if not e:
            print(f"  WARN missing q{qn}")
            continue
        al = e['answer']
        al_disp = '一律送分' if al == '送分' else al
        mdlines = [f"### 第{qn}題 【答案：{al_disp}】", "", e['question']]
        for ch, o in zip('ABCD', e['options']):
            mdlines.append(f"({ch}) {o}" if o else f"({ch})")
        with open(os.path.join(OUT, f'q{qn:02d}.md'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(mdlines) + '\n')

    aj = {}
    for qn in range(1, nq + 1):
        a = ann.get(qn, {}).get('answer')
        aj[str(qn)] = a if a else None
    with open(os.path.join(OUT, f'answers_{year}.json'), 'w', encoding='utf-8') as f:
        json.dump(aj, f, ensure_ascii=False, indent=2)

    # report issues
    empties = []
    for qn in range(1, nq + 1):
        e = ann.get(qn)
        if e:
            empty = [ch for ch, o in zip('ABCD', e['options']) if not o]
            if empty:
                empties.append((qn, empty))
        else:
            print(f"Q{qn:02d}: MISSING")
    print(f"Parsed {len(ann)}/{nq} questions.")
    miss = [q for q in range(1, nq + 1) if q not in ann]
    print(f"Missing: {miss}")
    if empties:
        print(f"EMPTY opts: {empties}")

    # ---------- crop images from EXAM PDF ----------
    doc = fitz.open(EXAM)
    page_pix = {}
    for pi in range(len(doc)):
        pix = doc[pi].get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
        page_pix[pi + 1] = pix
    doc.close()

    with pdfplumber.open(EXAM) as pdf:
        qpos = {}
        for pi, page in enumerate(pdf.pages, 1):
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            for wd in words:
                t = wd['text'].strip()
                m = re.match(r'^\[(' + ANS_CH + r')\]$', t)
                if not m:
                    continue
                y = wd['top']
                # look for following "N." token on same line.
                # Some years inline the number with the text (`1.求右圖...`).
                below = [w for w in words if abs(w['top'] - y) < 7
                         and re.match(r'^(\d{1,2})[、.．]', w['text'].strip())]
                if not below:
                    continue
                # problem: the score number might match too; choose the token
                # closest to/right of the bracket
                below.sort(key=lambda w: w['x0'])
                cands = [w for w in below if w['x0'] >= wd['x0'] - 2]
                nxt = cands[0] if cands else below[0]
                qn = int(re.match(r'^(\d{1,2})', nxt['text'].strip()).group(1))
                qpos[qn] = (pi, min(y, nxt['top']))
        bypage = {}
        for qn, (pi, y) in qpos.items():
            bypage.setdefault(pi, []).append((qn, y))
        ranges = {}
        for pi, lst in bypage.items():
            lst.sort(key=lambda x: x[1])
            page_h = pdf.pages[pi - 1].height
            for idx, (qn, y) in enumerate(lst):
                y_start = max(0, y - 8)
                y_end = lst[idx + 1][1] - 8 if idx + 1 < len(lst) else page_h
                ranges[qn] = (pi, y_start, y_end)

    missing_img = []
    for qn in range(1, nq + 1):
        if qn not in ranges:
            missing_img.append(qn)
            continue
        pi, y0, y1 = ranges[qn]
        pix = page_pix[pi]
        y0_px = max(0, int(round(y0 * SCALE)))
        y1_px = min(pix.height, int(round(y1 * SCALE)))
        if y1_px <= y0_px:
            missing_img.append(qn)
            continue
        pil = PILImage.frombytes('RGB', (pix.width, pix.height), pix.samples)
        crop = pil.crop((0, y0_px, pix.width, y1_px))
        crop.save(os.path.join(OUT, f'q{qn:02d}.png'))
    print(f"Images missing: {missing_img}")
    print(f"Pages with qpos: {sorted({pi for pi,_ in qpos.values()})}")
    print(f"Total qpos: {len(qpos)}")


if __name__ == '__main__':
    keys = sys.argv[1:] if len(sys.argv) > 1 else ['default']
    for k in keys:
        main(k)
