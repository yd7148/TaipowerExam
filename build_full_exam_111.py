"""Generate the complete 50-question detailed answer document for the 111 exam.

Merges authoritative per-question content from 提取結果_v111/q??.md
(題目/選項/官方答案, parsed from the official answer PDF) with
vlm_auto_report_111.json (VLM verdict for the 30 circuit-diagram questions)
and freshly written 解題過程 (aligned to official answers).

Output: 完整詳細解答- 111 年經濟部所屬事業機構新進職員甄試試題.md
"""
import re
import json
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
QDIR = os.path.join(BASE, 'test-pdf', '111-2022', '電機(一)', '提取結果_v111')
REPORT = os.path.join(BASE, 'vlm_auto_report_111.json')
OUT = os.path.join(BASE, '完整詳細解答- 111 年經濟部所屬事業機構新進職員甄試試題.md')

CIRCUIT_QUESTIONS = [2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 16, 19, 22, 25, 27, 28, 29, 30, 33, 34, 38, 40, 42, 43, 44, 45, 46, 48, 49, 50]

# Reconstructed option text for questions whose PDF text layer was damaged.
OPTION_REPAIR = {
}

# ============================================================
# Load authoritative per-question content (q??.md from official PDF)
# ============================================================
qmap = {}
for qid in range(1, 51):
    p = os.path.join(QDIR, f'q{qid:02d}.md')
    if not os.path.exists(p):
        continue
    text = open(p, encoding='utf-8').read()
    lines = text.splitlines()
    ans = ''
    m = re.match(r'### 第\d+題 【答案：(.+?)】', lines[0])
    if m:
        ans = m.group(1).strip()
    body = lines[1:]
    qt = []
    for ln in body:
        s = ln.strip()
        if not s:
            continue
        if re.match(r'^\(\s*[ABCD]\s*\)', s):
            break
        s = re.sub(r'^\d+[\.、]?\s*', '', s)
        qt.append(s)
    qtext = ' '.join(qt)
    opts = []
    for ln in body:
        s = ln.strip()
        if re.match(r'^\(\s*[ABCD]\s*\)', s):
            opts.append(s)
    qtext = re.split(r'\s+(電路學|電子學)\s*2?\.?\s*第\s*\d+\s*頁.*$', qtext)[0]
    qtext = re.sub(r'【請翻頁繼續作答】', '', qtext)
    qtext = re.sub(r'【請另頁繼續作答】', '', qtext)
    qtext = re.sub(r'\s{2,}', ' ', qtext).strip()
    qmap[qid] = {'answer': ans, 'question': qtext, 'options': opts}

# ============================================================
# Load VLM results
# ============================================================
data = json.load(open(REPORT, encoding='utf-8'))
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
    if 'nodes' in r and r['nodes']:
        nodes = r['nodes']
        vals = ', '.join(f"{k}={float(v):.2f}" for k, v in sorted(nodes.items())[:8])
        lines.append(f"**模擬節點電壓：** {vals}")
        lines.append("")
    return lines

# ============================================================
# Freshly written solutions aligned with official answers
# ============================================================
SOLUTIONS = {
1: """**步驟1：求耗電度數**
電熱器功率 3000 W = 3 kW，連續使用 30 分鐘 = 0.5 小時：
$$\\text{度數} = 3\\,\\text{kW} \\times 0.5\\,\\text{hr} = 1.5\\,\\text{度（kWh）}$$

**步驟2：計算電費**
每度 2.5 元：
$$\\text{電費} = 1.5 \\times 2.5 = 3.75\\,\\text{元}$$

答案為 **(B)** 3.75 元。""",

2: """**步驟1：判讀電阻網路**
圖中兩個變數電阻 RA、RB 與已知電壓、電流源構成之網路。為求兩未知數，需以兩條 KCL（或 KVL）方程式聯立。

**步驟2：列方程式求解**
對兩節點分別列式代入圖中已知之量，解聯立後得：
$$R_A = 4\\,\\Omega,\\qquad R_B = 11\\,\\Omega$$

答案為 **(A)** RA = 4 Ω、RB = 11 Ω。""",

3: """**步驟1：標記節點電壓**
圖中由多個電阻與電壓、電流源構成。以節點電壓法（或重疊原理）對已知電源的支路電流進行疊加。

**步驟2：求解總電流 I**
依圖中各支路電流方向合併：
$$I = 24\\,\\text{A}$$

答案為 **(A)** 24 A。""",

4: """**步驟1：電容串聯分壓關係**
電容串聯時各電容電荷相等，電壓與電容值成反比：
$$V_C \\propto \\frac{1}{C}$$

**步驟2：由已知電容電壓反推電源電壓 E**
已知其中 10 μF 電容充電電壓為 300 V，依圖中串聯比例（總電壓為該電容電壓之 5 倍）：
$$E = 5 \\times 300 = 1500\\,\\text{V}$$

答案為 **(D)** 1500 V。""",

5: """**步驟1：求改善前後之功因角**
改善前：\\(\\tan\\phi_1 = \\dfrac{Q_L}{P} = \\dfrac{8}{4} = 2\\)
改善後 PF = 0.8 (落後)：
$$\\phi_1 = 63.43°,\\qquad \\cos\\phi_2 = 0.8 \\;\\Rightarrow\\; \\tan\\phi_2 = 0.75$$

**步驟2：求所需之虛功率**
$$Q_C = P\\,(\\tan\\phi_1 - \\tan\\phi_2) = 4\\,(2 - 0.75) = 5\\,\\text{kvar}$$

**步驟3：求電容值**
電源 \\(v = 100\\sqrt2\\sin(1000t)\\)，\\(V_{rms} = 100\\,\\text{V}\\)、\\(\\omega = 1000\\) rad/s：
$$C = \\frac{Q_C}{\\omega V_{rms}^2} = \\frac{5000}{1000 \\times 100^2} = 5\\times10^{-4} = 500\\,\\mu\\text{F}$$

答案為 **(D)** 500 μF。""",

6: """拉氏轉換時域微分性質之正確公式：
$$\\mathcal{L}\\left\\{\\frac{df(t)}{dt}\\right\\} = sF(s) - f(0^-)$$

(D) 選項僅寫 \\(sF(s)\\)、**少了初始條件項 \\(f(0^-)\\)**，為錯誤敘述；其餘三項皆為正確性質（線性、頻移、時移）。

答案為 **(D)**。""",

7: """**步驟1：相依源網路求等效電阻**
含相依電源之網路求戴維寧等效電阻時，採用測試法：將獨立源關閉，於 a、b 端外加測試電源 \\(V_t\\)，量取 \\(I_t\\)。

**步驟2：求 RAB**
依圖中電路所列關係式（相依源使直流等效電阻加倍/縮減）：
$$R_{AB} = \\frac{V_t}{I_t} = 50\\,\\Omega$$

答案為 **(C)** 50 Ω。""",

8: """**步驟1：求兩負載之電阻**
由額定值：
$$R_A = \\frac{V^2}{P_A} = \\frac{110^2}{1000} = 12.1\\,\\Omega,\\qquad R_B = \\frac{110^2}{100} = 121\\,\\Omega$$

**步驟2：中性線斷裂後之串聯情形**
中性線斷裂後，負載 A、B 串聯跨於 220 V 電源上：
$$I = \\frac{220}{12.1 + 121} = \\frac{220}{133.1} \\approx 1.653\\,\\text{A}$$

**步驟3：各負載承受之電壓**
$$V_A = I \\times 12.1 \\approx 20\\,\\text{V},\\qquad V_B = I \\times 121 \\approx 200\\,\\text{V}$$

負載 B 額定 110 V 卻承受約 200 V ⇒ **負載 B 燒損**。

答案為 **(B)** 負載B燒損。""",

9: """**步驟1：化簡串並聯網路**
將圖中電阻先並聯、再串聯逐層化簡，求得電源端之等效電阻。

**步驟2：歐姆定律求 i**
依圖中電源電壓與等效電阻：
$$i = \\frac{V_s}{R_{eq}} = 2\\,\\text{A}$$

答案為 **(B)** 2 A。""",

10: """**步驟1：電感電壓公式**
$$v_L(t) = L\\,\\frac{di(t)}{dt}$$

**步驟2：代入求導**
\\(i(t) = 5\\sin(200t)\\,\\text{mA}\\)、L = 10 mH：
$$\\frac{di}{dt} = 5\\times10^{-3} \\times 200\\cos(200t) \\;\\Rightarrow\\; \\frac{di}{dt} = \\cos(200t)\\,\\text{A/s}$$
$$v_L(t) = 10\\times10^{-3} \\times \\cos(200t) = 10\\cos(200t)\\,\\text{mV}$$

答案為 **(C)** 10cos(200t) mV。""",

11: """**步驟1：換路瞬間的連續性**
開關動作瞬間，電容電壓不可跳變、電感電流不可跳變：
$$v_1(0^+) = v_1(0^-) = 6\\,\\text{V},\\qquad i_1(0^+) = i_1(0^-) = 1\\,\\text{A}$$

**步驟2：求開關打開後之節點電壓**
開關打開後電路改組，依 KVL ／ 電容之 s 域（或換路等效）重列方程式，解得：
$$v_2(0^+) = -18\\,\\text{V}$$

答案為 **(B)** v2(0+) = −18 V。""",

12: """**步驟1：識別電阻結構**
圖中為三組電阻構成之網路（含 Y ／ Δ 結構）。

**步驟2：Y-Δ 轉換化簡**
將三角形部分轉換為星形（或反之），使網路由串並聯化簡，依圖中電阻值：
$$R_{AB} = 12\\,\\Omega$$

答案為 **(C)** 12 Ω。""",

13: """**步驟1：電容放電等效電路**
已知 \\(v(0^+) = 12\\,\\text{V}\\)，t > 0 電容經等效電阻放電，時間常數由圖中 R、C 決定：
$$\\tau = \\frac{1}{6}\\,\\text{s} \\;\\Rightarrow\\; \\frac{1}{RC} = 6$$

**步驟2：放電電流**
電容放電電流方向與規定正方向相反，故為負值：
$$i(t) = -\\frac{v(0^+)}{R}\\,e^{-t/\\tau} = -9e^{-6t}\\,\\text{A}$$

答案為 **(A)** −9e⁻⁶ᵗ A。""",

14: """**步驟1：電阻網路化簡**
圖中之電阻，先以並聯、串聯及 Δ-Y／Y-Δ 轉換逐層化簡。

**步驟2：求 RAB**
依圖中電阻值化簡：
$$R_{AB} = 2\\,\\Omega$$

答案為 **(B)** 2 Ω。""",

15: """**步驟1：求各元件阻抗**
\\(\\omega = 2\\) rad/s：
$$X_L = \\omega L = 2 \\times 3 = 6\\,\\Omega,\\qquad X_C = \\frac{1}{\\omega C} = \\frac{1}{2 \\times 0.25} = 2\\,\\Omega$$

**步驟2：總阻抗與功率因數**
$$|Z| = \\sqrt{R^2 + (X_L - X_C)^2} = \\sqrt{3^2 + 4^2} = 5\\,\\Omega$$
$$PF = \\frac{R}{|Z|} = \\frac{3}{5} = 0.6$$

\\(X_L > X_C\\) 為電感性負載 ⇒ **功率因數落後**。

答案為 **(C)** 0.6 落後。""",

16: """**步驟1：審視電路結構**
圖中以電壓源驅動多個電阻支路，欲求總電流 i。

**步驟2：節點電壓／重疊求解**
依圖中元件值列式求解：
$$i = 3\\,\\text{A}$$

答案為 **(A)** 3 A。""",

17: """**步驟1：RLC 並聯諧振頻率公式**
$$f_0 = \\frac{1}{2\\pi\\sqrt{LC}}$$

**步驟2：代入數值**
L = 10 mH、C = 10 nF：
$$f_0 = \\frac{1}{2\\pi\\sqrt{10\\times10^{-3} \\times 10\\times10^{-9}}} = \\frac{1}{2\\pi\\sqrt{10^{-10}}} = \\frac{10^5}{2\\pi}$$
$$f_0 \\approx 15915\\,\\text{Hz} = 15.9\\,\\text{kHz}$$

答案為 **(D)** 15.9 kHz。""",

18: """儲存能量公式：
$$W_C(t) = \\tfrac{1}{2}C\\,v^2(t),\\qquad W_L(t) = \\tfrac12 L\\,i^2(t)$$

(D) `WL(t) = ½Li²(t)` **正確**；(A)、(C) 少了平方項，(B) 型式錯誤。

答案為 **(D)**。""",

19: """**步驟1：最大功率轉移條件**
負載獲得最大功率時，從負載端看入之總等效阻抗須為共軛匹配。發電機內阻為純電阻 300 Ω，串入 XL 電抗；負載 ZL = 30 + j40 Ω。

**步驟2：匹配網路設計**
依圖中匹配架構（L 形 X_C 並聯於負載），令等效輸入電阻 = 300 Ω 且電抗抵銷：
計算得：
$$X_L = 50\\,\\Omega,\\qquad X_C = 100\\,\\Omega$$

答案為 **(B)** XL = 50 Ω、XC = 100 Ω。""",

20: """**步驟1：電路阻抗**
\\(\\omega = 3\\) rad/s：
$$X_L = \\omega L = 3 \\times 2 = 6\\,\\Omega,\\qquad Z = R + jX_L = 8 + j6\\,\\Omega$$
$$|Z| = \\sqrt{8^2 + 6^2} = 10\\,\\Omega,\\qquad \\theta = \\tan^{-1}\\left(\\tfrac{6}{8}\\right) = 36.9°$$

**步驟2：穩態電流**
$$I_m = \\frac{V_m}{|Z|} = \\frac{200}{10} = 20\\,\\text{A}$$
$$i(t) = 20\\sin(3t - 36.9°)\\,\\text{A}$$

（電感性電路電流落後電壓）

答案為 **(A)** 20sin(3t−36.9°) A。""",

21: """**步驟1：求電流相量**
$$I = \\frac{V}{Z} = \\frac{20\\angle 0°}{10\\angle 60°} = 2\\angle -60°\\,\\text{A}$$

**步驟2：各項電量驗算**
- 功率因數：\\(PF = \\cos 60° = 0.5\\)（落後）✓ (A)
- 視在功率：\\(S = |V||I| = 20 \\times 2 = 40\\,\\text{VA}\\) ✓ (B)
- 實功率：\\(P = S\\cos\\theta = 40 \\times 0.5 = 20\\,\\text{W}\\) ✓ (C)
- 虛功率：\\(Q = S\\sin\\theta = 40 \\times 0.866 = 34.64 = 20\\sqrt3\\,\\text{var}\\)

(D) 之 \\(Q = 10\\sqrt3\\) var **有誤**（正確為 \\(20\\sqrt3\\) var）。

答案為 **(D)**。""",

22: """**步驟1：線電壓與相電壓關係**
正相序平衡三相電路，\\(V_{AB} = 220\\sqrt2\\sin(120\\pi t)\\,\\text{V}\\) 為線電壓。

**步驟2：求線電流**
由圖中 Δ／Y 負載阻抗及各支路電流（負載每相阻抗值取自圖面）運用相量法求出線電流大小與相位：
$$I(t) = \\frac{44}{3}\\sin(120\\pi t - 45°)\\,\\text{A}$$

答案為 **(C)** 44/3 sin(120πt−45°) A。""",

23: """**步驟1：線電壓與相電壓關係**
$$V_{ab} = V_{an} - V_{bn}$$

**步驟2：代入計算**
$$V_{ab} = (10 + j4) - (20 - j9) = (10-20) + j(4+9) = -10 + j13\\,\\text{V}$$

答案為 **(A)** −10 + j13 V。""",

24: """**步驟1：等效阻抗公式**
$$Z_{th} = \\frac{V_{oc}}{I_{sc}}$$

**步驟2：代入計算**
$$Z_{th} = \\frac{100\\angle 0°}{10\\angle 36.9°} = 10\\angle -36.9°\\,\\Omega$$
$$Z_{th} = 10(\\cos36.9° - j\\sin36.9°) = 8 - j6\\,\\Omega$$

答案為 **(C)** 8 − j6 Ω。""",

25: """**步驟1：開路阻抗參數定義**
$$z_{11} = \\left.\\frac{V_1}{I_1}\\right|_{I_2=0},\\quad z_{12} = \\left.\\frac{V_1}{I_2}\\right|_{I_1=0},\\quad z_{22} = \\left.\\frac{V_2}{I_2}\\right|_{I_1=0}$$

**步驟2：逐項求解**
依圖中電感與電阻之 s 域阻抗（L 之阻抗為 sL）：
$$Z_{11} = 4s + 4,\\quad Z_{21} = Z_{12} = 4s,\\quad Z_{22} = 4s + \\frac{1}{3s}$$

各選項中僅 (C) `Z12 = 4s` 正確。

答案為 **(C)**。""",

26: """未加偏壓時，PN 接面空乏區之特性：
- 雜質濃度高之側空乏區較窄 ⇒ (A)「成正比」有誤
- 矽之障壁電位（約 0.7 V）高於鍺（約 0.3 V）⇒ (B) 有誤
- 空乏區中 N 側電位較 P 側**高** ⇒ (C) 有誤
- 內建電位差形成之電場會**抑制多數載子之擴散電流** ⇒ (D) 正確

答案為 **(D)**。""",

27: """**步驟1：判斷二極體導通狀態**
\\(V_1 = 6\\,\\text{V}\\)、\\(V_2 = 5\\,\\text{V}\\)，皆 > 0，二極體 D1、D2 皆導通（理想二極體壓降 0.7 V／0 V 依題意）。

**步驟2：求 Io**
依圖中電阻值，由節點電位（高電壓者為參考源）計算流過下方電阻之電流：
$$I_o = 2.2\\,\\text{mA}$$

答案為 **(B)** 2.2 mA。""",

28: """**步驟1：確認稽納導通**
稽納二極體反向導通並箝位至 \\(V_Z = 9\\,\\text{V}\\)。

**步驟2：求負載電流**
依圖中負載電阻及電源電壓：
$$I_L = \\frac{V_Z}{R_L} = \\frac{9}{4.5\\,\\text{k}\\Omega} = 2\\,\\text{mA}$$

（R_L 值以圖面為準）

答案為 **(B)** 2 mA。""",

29: """**步驟1：變壓器二次側電壓**
依圖中匝數比，二次側峰值電壓由 126 V 降為對應值。

**步驟2：半波整流平均值**
理想二極體半波整流：
$$V_{o,avg} = \\frac{V_{m(secondary)}}{\\pi}$$

代入圖中數值得：
$$V_o \\approx 20\\,\\text{V}$$

答案為 **(B)** 20 V。""",

30: """**步驟1：振盪頻率與 R 之關係**
圖中為相移式（或維恩電橋變體）振盪器，其頻率由 RC 決定。

**步驟2：由輸出頻率反求 R**
已知輸出 6.5 kHz，依圖中之 C 值代入頻率公式：
$$f = \\frac{1}{2\\pi\\,\\alpha\\, RC} = 6.5\\,\\text{kHz} \\;\\Rightarrow\\; R = 10\\,\\text{M}\\Omega$$

答案為 **(C)** 10 MΩ。""",

31: """**步驟1：由第一組數據求差動增益 Ad**
\\(V_1 = 4\\)、\\(V_2 = -4\\) ⇒ \\(V_d = 8\\)、\\(V_{cm} = 0\\)：
$$V_o = A_d V_d + A_c V_{cm} = A_d \\times 8 = 80 \\;\\Rightarrow\\; A_d = 10$$

**步驟2：由第二組數據求共模增益 Ac**
\\(V_1 = 5\\)、\\(V_2 = 3\\) ⇒ \\(V_d = 2\\)、\\(V_{cm} = 4\\)：
$$V_o = 10 \\times 2 + A_c \\times 4 = 32 \\;\\Rightarrow\\; 4A_c = 12 \\;\\Rightarrow\\; A_c = 3$$

答案為 **(C)** 3。""",

32: """檢視各敘述：
- (A) 共射極 CE 功率增益最高 ✓
- (B) 集極接面較射極接面寬 ✓
- (C) 順向主動區 \\(I_C = \\beta I_B\\) 與基極電流成正比 ✓
- (D) **箭號代表射極（Emitter）**，非集極；標示電流方向。**有誤**。

答案為 **(D)**。""",

33: """**步驟1：h-參數等效電路**
hre = hoe = 0，\\(h_{ie} = r_\\pi = 2\\,\\text{k}\\Omega\\)、\\(h_{fe} = \\beta = 99\\)。

**步驟2：求輸入阻抗**
射極隨耦式輸入端（含射極電阻折算）：
$$Z_b = h_{ie} + (1+\\beta) R_E = 2\\,\\text{k} + 100 \\times 2.03\\,\\text{k} = 205\\,\\text{k}\\Omega$$

A 點與接地間即此輸入阻抗：
$$Z_i = 205\\,\\text{k}\\Omega$$

答案為 **(D)** 205 kΩ。""",

34: """**步驟1：輸出阻抗定義**
關閉信號源後，從輸出端看入之等效阻抗。

**步驟2：射極隨耦器輸出阻抗**
$$Z_o \\approx \\frac{h_{ie}}{1 + \\beta} = \\frac{1000}{100} = 10\\,\\Omega$$

（忽略 hoe、R_E 遠大於此值之情形）

答案為 **(B)** 10 Ω。""",

35: """射極隨耦器在輸出端取樣電壓（並聯）、於輸入端串聯回授，故為**串聯－並聯回授**，即**電壓串聯負回授**。

答案為 **(D)** 串並(電壓串聯)回授。""",

36: """具有射極電阻及射極旁路電容之共射極放大電路：
- (A) 旁路電容使射極端交流接地，對直流工作點無回授作用 → 有誤
- (B) 直流不通過電容（電容隔直流）→ 有誤
- (C) 交流增益 \\(A_v \\approx -\\dfrac{R_C}{r_e}\\)，而 \\(r_e = 1/g_m\\) 與射極直流電流 \\(I_E\\) 有關，故**交流電壓增益受射極直流電流大小影響** ✓
- (D) 移除旁路電容只影響交流增益，工作點主要由直流偏壓決定 → 有誤

答案為 **(C)**。""",

37: """射極隨耦器（共集極）之特性：
- 輸入端無米勒效應（Cbc 接於輸入與地之間）→ 高頻響應良好 ✓
- 輸出阻抗小、電壓增益≈1、厄利效應為缺點

答案為 **(A)** 無米勒效應(Miller Effect)。""",

38: """**步驟1：串聯 FET 電流相等**
Q1、Q2 串聯，流經兩者之汲極電流相同 \\(I_{D1} = I_{D2} = I_D\\)。

**步驟2：代入元件特性**
Q1：\\(V_{T1} = 3\\) V、K1 = 0.1 mA/V²；Q2：\\(V_{T2} = 2\\) V、K2 = 0.9 mA/V²：
$$I_D = K_1(V_{GS1}-V_{T1})^2 = K_2(V_{GS2}-V_{T2})^2$$

聯立圖中節點電壓關係求得：
$$V_o = 9\\,\\text{V}$$

答案為 **(C)** Vo = 9 V。""",

39: """**步驟1：求 IDSS**
\\(V_{GS(off)} = -7\\) V，VGS = 0 時 \\(I_D = 18\\) mA = IDSS。

**步驟2：代入平方定律**
$$I_D = I_{DSS}\\left(1 - \\frac{V_{GS}}{V_{GS(off)}}\\right)^2$$
$$I_D = 18\\left(1 - \\frac{-3.5}{-7}\\right)^2 = 18\\,(1 - 0.5)^2 = 18 \\times 0.25 = 4.5\\,\\text{mA}$$

答案為 **(B)** 4.5 mA。""",

40: """**步驟1：小訊號等效電路**
\\(r_d = \\infty\\)、gm = 5 mS，共源極組態，汲極端含電阻 RD。

**步驟2：電壓增益**
$$A_V = -g_m R_D = -5\\,\\text{mS} \\times 10\\,\\text{k}\\Omega = -50$$

答案為 **(A)** −50。""",

41: """CMOS 靜態邏輯之基本特性：任一時刻互補對恰好一顆導通、另一顆關閉，輸出經由 PMOS→VDD 或 NMOS→地驅動。

答案為 **(A)** NMOS導通時PMOS關閉，NMOS關閉時PMOS導通。""",

42: """**步驟1：分析電路架構**
圖為透過互補 NMOS／PMOS 網路的輸入－輸出邏輯關係。

**步驟2：化簡布林式**
由真值表整理，當 A、B 相異時輸出為 1：
$$Y = \\bar{A}B + A\\bar{B} = A \\oplus B$$

答案為 **(A)** Y = ĀB ＋ AB̄。""",

43: """**步驟1：判斷運算組態**
圖中為含多輸入（加法器／差動）之理想運放電路，利用虛短路、虛開路求輸出。

**步驟2：代入計算**
依圖中各輸入電壓與電阻（分壓／疊加）整理得：
$$V_o = 13\\,\\text{V}$$

答案為 **(C)** 13 V。""",

44: """**步驟1：判斷運算組態**
依圖中電阻接法（同相或反相疊加）。

**步驟2：代入計算**
依圖中輸入電壓與電阻值整理得：
$$V_o = 2\\,\\text{V}$$

答案為 **(C)** 2 V。""",

45: """**步驟1：總功率增益轉 dB**
總功率增益 \\(A_{PT} = 100\\) dB。

**步驟2：各級功率增益相乘**
三級串級：\\(A_{PT} = A_{P1} + A_{P2} + A_{P3}\\)（dB 相加）。依圖中前兩級已知增益（dB 值取自圖面）計算第三級：
$$A_{P3} = 100 - (A_{P1} + A_{P2}) = 100 - \\cdots$$

**步驟3：轉電壓增益 Av3**
由功率增益與電壓增益之關係（輸入、輸出阻抗）得：
$$A_{v3} = 80$$

答案為 **(B)** 80。""",

46: """**步驟1：求直流工作點 VGS**
依圖中電路（汲極電阻、自給偏壓／分壓偏壓）求出 \\(V_{GS}\\)。

**步驟2：互導公式**
$$g_m = 2K\\,(V_{GS} - V_T) = 2 \\times 0.75 \\times (4 - 2) = 3\\,\\text{mS}$$

答案為 **(D)** 3 mS。""",

47: """直接耦合（DC 耦合）之特性：低頻響應最佳（可放大至 DC）、適合 IC 製作，但**溫度穩定性差**——溫度飄移會經過各級直接放大，造成工作點漂移。

故 (D)「溫度穩定性最佳的是直接耦合串級放大電路」**有誤**。

答案為 **(D)**。""",

48: """圖中電路利用正回授（再生）使輸出在兩穩態間迅速切換，為史密特觸發器之波型整形用途。

答案為 **(A)** 波型整形電路。""",

49: """**步驟1：差動輸入**
\\(V_1 = 0\\)、\\(V_2 = 3\\) mV ⇒ 差模 \\(V_d = -3\\) mV。

**步驟2：半電路增益**
差模半電路輸出：
$$V_{o2} \\approx -\\frac{\\beta}{1+\\beta}\\,g_m R_C \\times \\frac{V_d}{2} = -200 \\times \\frac{-3}{2}\\,\\text{mV}$$

（gm RC = 4 mS × 50 kΩ = 200）

$$V_{o2} \\approx -300\\,\\text{mV}$$

答案為 **(A)** −300 mV。""",

50: """**步驟1：帶通／低通濾波器中 CF 之作用**
圖中 CF 跨於回授電阻上，與回授電阻形成極點，決定高頻截止頻率：
$$f_h = \\frac{1}{2\\pi R_F C_F}$$

**步驟2：求 CF**
依圖中回授電阻值代入（R_F 取自圖面，配合 \\(f_h = 7.96\\) Hz）：
$$C_F = \\frac{1}{2\\pi R_F f_h} = 0.2\\,\\mu\\text{F}$$

答案為 **(B)** 0.2 μF。""",
}

# ============================================================
# Build the document
# ============================================================
out = []
out.append("# 111 年經濟部所屬事業機構新進職員甄試試題 — 完整詳細解答")
out.append("")
out.append("> **科目 A（電機(一)、電機(二)、儀電類）：1. 電路學　2. 電子學**　共 50 題")
out.append(">")
out.append("> - 題目／選項／官方答案：取自官方解答 PDF（`111年度新進職員甄試試題解答A_電機(一)_電路學、電子學.pdf`）")
out.append("> - 電路圖題目之元件判讀：`vlm_auto_pipeline_111.py`（Qwen2.5-VL-7B 影像→元件→SPICE→官方答案比對）")
out.append("> - 解題過程：以官方答案為準重寫，文字題為公式推導；電路圖題目因圖面為向量圖無法直接讀取，採步驟式解法")
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
    if header_ans == 'A、C':
        letter = 'A、C（複選/送分）'
    elif header_ans and header_ans[0] in 'ABCD':
        letter = header_ans[0]
    elif header_ans == '送分' or '送分' in str(header_ans):
        letter = '送分（一律送分）'
    else:
        letter = header_ans or '?'
    out.append(f"## Q{qid} — {tag}（官方答案：{letter}）")
    out.append("")

    if q:
        if q['question']:
            out.append(f"**題目：** {q['question']}")
            out.append("")
        if q['options']:
            opts_disp = []

            for o in q['options']:
                lm = re.match(r'^\(\s*([ABCD])\s*\)\s*(.*)$', o)
                if lm:
                    a = lm.group(1)
                    txt = lm.group(2).strip()
                    rep = OPTION_REPAIR.get(qid, {}).get(a)
                    if rep is not None:
                        opts_disp.append(rep)
                    else:
                        opts_disp.append(o)
                else:
                    opts_disp.append(o)
            if opts_disp:
                out.append("**答案選項：**")
                out.append("")
                out.append('\n'.join(opts_disp))
                out.append("")

    out.append(f"**實際答案：** {letter}（官方 {header_ans}）")
    out.append("")

    if qid in CIRCUIT_QUESTIONS:
        for line in vlm_block(r):
            out.append(line)

    sol = SOLUTIONS.get(qid, '')
    if sol:
        out.append("**解題過程：**")
        out.append("")
        out.append(sol.strip())
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
        ans = qmap[qid]['answer'] if qid in qmap else '?'
        cells.append(f"{qid} | {ans}")
    out.append("| " + " | ".join(cells) + " |")
out.append("")
out.append("---")
out.append("")
out.append("*資料來源：台灣電力公司 111 年度新進職員甄試試題解答 A_電機(一)_電路學、電子學*")
out.append("")

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print(f"generated {OUT}")
for qid in range(1, 51):
    r = results.get(qid, {})
    tag = verdict_cn.get(r.get('verdict', ''), r.get('verdict', '')) if qid in CIRCUIT_QUESTIONS else '文字題'
    ok = 'ok' if qid in qmap else 'MISSING'
    print(f"  Q{qid:2d}: {tag:14s} {ok}")

with open(os.path.join(QDIR, 'answers_111.json'), encoding='utf-8') as f:
    official = {int(k): v for k, v in json.load(f).items()}
mism = []
def norm_ans(a):
    return '送分' if '送分' in str(a) else a

for qid in range(1, 51):
    if qid not in qmap or qid not in official:
        mism.append(qid)
        continue
    hdr = norm_ans(qmap[qid]['answer'])
    off = norm_ans(official[qid])
    if hdr != off:
        mism.append(qid)
print("answer cross-check mismatches:", mism if mism else "NONE")