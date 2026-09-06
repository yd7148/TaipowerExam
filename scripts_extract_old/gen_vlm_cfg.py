# -*- coding: utf-8 -*-
"""Generate vlm_cfg_<key>.json for a year from its extraction folder.
Auto-detects circuit questions by scanning q??.md for diagram keywords.
Usage: python gen_vlm_cfg.py <year_key> [<year_key>...]
"""
import io, sys, os, re, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = r'E:\01-Project\2026-08-Taipower-test\test-pdf'

# year_key: (exam_dir, out_suffix, n_questions)
CFG = {
    '108': (r'108-2019\電機', 'v108', 50),
    '107': (r'107-2018\電機', 'v107', 50),
    '106甲': (r'106-2017\電機(甲)', 'v106a', 50),
    '106乙': (r'106-2017\電機(乙)', 'v106b', 50),
    '105甲': (r'105-2016\電機(甲)', 'v105a', 50),
    '105乙': (r'105-2016\電機(乙)', 'v105b', 50),
    '104甲': (r'104-2015\電機(甲)', 'v104a', 50),
    '104乙': (r'104-2015\電機(乙)', 'v104b', 50),
    '103乙': (r'103-2014\電機(乙)', 'v103b', 40),
}

FIG_HINT = re.compile(r'如右圖|如圖|右圖|下圖|圖中|圖示|如[下上]圖|如右圖所示|電路圖|ﾓ圖')

def build(key):
    exam_dir, suffix, nq = CFG[key]
    year = key.rstrip('甲乙')
    img_dir = os.path.join(BASE, exam_dir, f'提取結果_{suffix}')
    # answers
    aj = json.load(open(os.path.join(img_dir, f'answers_{year}.json'), encoding='utf-8'))
    answer_letters = {str(i): (aj.get(str(i)) or '?') for i in range(1, nq + 1)}
    # circuit questions + question text
    circ = []
    qtext = {}
    for i in range(1, nq + 1):
        p = os.path.join(img_dir, f'q{i:02d}.md')
        lines = open(p, encoding='utf-8').read().splitlines()
        body = '\n'.join(l for l in lines if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('來源'))
        qtext[str(i)] = re.sub(r'\s+', ' ', body).strip()[:400]
        if FIG_HINT.search(body) or (os.path.exists(os.path.join(img_dir, f'q{i:02d}.png')) and i in () ):
            circ.append(i)
    # Fallback: any question whose .png differs from a blank/text-only crop is a diagram.
    # Simpler robust rule: keep FIG_HINT result (used for 103甲); images exist for all.
    cfg = {
        'image_base': img_dir,
        'circuit_questions': circ,
        'answer_letters': answer_letters,
        'answer_values': {},
        'question_text': qtext,
        'report': f'vlm_auto_report_{key}.json',
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'vlm_cfg_{key}.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"{key}: {len(circ)}/{nq} circuit questions -> {os.path.basename(out)}")
    print("  circ:", circ)

if __name__ == '__main__':
    for k in sys.argv[1:]:
        build(k)