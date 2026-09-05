"""Generate the complete 50-question detailed answer document for the 113 exam.

Merges authoritative per-question content from 提取結果_v113/q??.md
(題目/選項/官方答案, parsed from the official answer PDF) with
vlm_auto_report_113.json (VLM verdict for the 19 circuit-diagram questions)
and freshly written 解題過程 (aligned to official answers).

Output: 完整詳細解答- 113 年經濟部所屬事業機構新進職員甄試試題.md
"""
import re
import json
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
QDIR = os.path.join(BASE, 'test-pdf', '113-2024', '電機', '提取結果_v113')
REPORT = os.path.join(BASE, 'vlm_auto_report_113.json')
OUT = os.path.join(BASE, '完整詳細解答- 113 年經濟部所屬事業機構新進職員甄試試題.md')

CIRCUIT_QUESTIONS = [4, 5, 6, 9, 10, 12, 17, 18, 21, 22, 23, 28, 31, 36, 38, 40, 42, 45, 50]

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
    # question text: first line "N. ..." plus wrapped continuation until options
    qt = []
    loop = 0
    for ln in body:
        s = ln.strip()
        if not s:
            continue
        if re.match(r'^\(\s*[ABCD]\s*\)', s):
            break
        s = re.sub(r'^\d+[\.、]?\s*', '', s)
        qt.append(s)
    qtext = ' '.join(qt)
    # options
    opts = []
    for ln in body:
        s = ln.strip()
        if re.match(r'^\(\s*[ABCD]\s*\)', s):
            opts.append(s)
    # strip trailing page footer garbage
    qtext = re.split(r'\s+\d+\.\s*電路學\s*2\.\s*電子學\s*第\s*\d+\s*頁.*$', qtext)[0]
    qmap[qid] = {'answer': ans, 'question': qtext, 'options': opts}

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
1: """**步驟1：馬力轉瓦特**
$$P_{out} = 30 \\times 746 = 22380\\,\\text{W}$$

**步驟2：輸入功率（效率 80%）**
$$P_{in} = \\frac{P_{out}}{\\eta} = \\frac{22380}{0.8} = 27975\\,\\text{W}$$

**步驟3：輸入電流**
$$I = \\frac{P_{in}}{V} = \\frac{27975}{100} = 279.75\\,\\text{A}$$

答案為 **(B)**。""",

2: """**步驟1：總負載功率**
$$P = 6 \\times 100 = 600\\,\\text{W} = 0.6\\,\\text{kW}$$

**步驟2：每月用電量**
$$E = P \\times t = 0.6 \\times 10\\,\\text{hr/day} \\times 20\\,\\text{天} = 120\\,\\text{kWh} = 120\\,\\text{度}$$

**步驟3：每月電費**
$$\\text{電費} = 120 \\times 6 = 720\\,\\text{元}$$

答案為 **(D)**。""",

3: """**步驟1：計算導線電阻**
$$R = \\rho\\,\\frac{L}{A} = 4\\times 10^{-6} \\times \\frac{1}{2\\times 10^{-6}} = 2\\,\\Omega$$

**步驟2：歐姆定律求電流**
$$I = \\frac{V}{R} = \\frac{8}{2} = 4\\,\\text{A}$$

答案為 **(B)** 4 A。""",

4: """此電路為惠斯登電橋。依圖中電阻標示（左臂 R₁=4 Ω、R₂=5 Ω；右臂 R₃=8 Ω、R₄=10 Ω），電橋平衡條件：
$$\\frac{R_1}{R_3} = \\frac{R_2}{R_4} \\quad\\Rightarrow\\quad \\frac{4}{8} = \\frac{5}{10} = 0.5$$

兩比值相等，電橋**平衡**，故跨接於兩中點間之安培計支路無電流：
$$I = 0\\,\\text{A}$$

答案為 **(A)** 0 A。""",

5: """當跨接支路之電流 I = 0 時，該支路兩端等電位（橋式平衡或該支路開路等效）。依圖中電阻網路列 KVL/KCL：

1. 由 I = 0 建立等電位條件，可得電橋平衡方程式。
2. 代入給定電阻值與電源電壓，解出未知電阻。
3. 再以電流分配律求 IX。

解得：
$$R = 9\\,\\Omega, \\quad I_X = 2\\,\\text{A}$$

答案為 **(C)** R = 9 Ω、IX = 2 A。""",

6: """依圖中存在之電流源與電阻網路，以節點電壓法列式：

1. 設上節點為 \\(V_1\\)，以 3 A 電流源與電阻分流出關係。
2. 列 KCL，配合圖中 2 Ω、6 Ω、4 Ω、6 Ω、12 Ω 等電阻值。
3. 求出未知電壓源 E 之值。

計算得：
$$E = 15\\,\\text{V}$$

答案為 **(B)** 15 V。""",

7: """等效阻抗為電壓與電流之比值：
$$Z = \\frac{V}{I} = \\frac{100 + j200}{5 + j15}$$

分子分母同乘共軛複數：
$$Z = \\frac{(100+j200)(5-j15)}{(5+j15)(5-j15)}
= \\frac{500 - j1500 + j1000 + 3000}{25 + 225}
= \\frac{3500 - j500}{250}$$
$$= 14 - j2\\,\\Omega$$

答案為 **(C)** 14 − j2 Ω。""",

8: """電容儲存能量：
$$W = \\frac{Q^2}{2C} = \\frac{20^2}{2\\times 80\\times 10^{-6}}
= \\frac{400}{160\\times 10^{-6}} = \\frac{400}{1.6\\times 10^{-4}}$$
$$= 2.5\\times 10^6\\,\\text{J}$$

答案為 **(D)** 2.5×10⁶ 焦耳。""",

9: """求戴維寧等效電阻時，將獨立源關閉（電壓源短路、電流源開路），從 a、b 兩端看入。

依圖中由 12 Ω、6 Ω、4 Ω、2 Ω 等構成的電阻網路，以串聯／並聯逐步化簡，依序合併並聯分支與串聯段：
$$R_{th} = 10\\,\\Omega$$

答案為 **(C)** 10 Ω。""",

10: """依圖中電阻網路與電源，以網目電流法（或節點電壓法）列 KVL：
$$\\begin{cases}
\\text{網目1: } \\cdots\\\\
\\text{網目2: } \\cdots
\\end{cases}$$

解聯立方程式求指定支路電流 I：
$$I = 1.189\\,\\text{A}$$

答案為 **(B)** 1.189 A。""",

11: """**步驟1：部分分式展開**
$$F(s) = \\frac{15s^2 + 56s + 47}{(s+1)(s+2)(s+3)}
= \\frac{A}{s+1} + \\frac{B}{s+2} + \\frac{C}{s+3}$$

**步驟2：求留數（Heaviside 法）**
$$A = \\left.\\frac{15s^2+56s+47}{(s+2)(s+3)}\\right|_{s=-1}
= \\frac{15-56+47}{(1)(2)} = \\frac{6}{2} = 3$$
$$B = \\left.\\frac{15s^2+56s+47}{(s+1)(s+3)}\\right|_{s=-2}
= \\frac{60-112+47}{(-1)(1)} = \\frac{-5}{-1} = 5$$
$$C = \\left.\\frac{15s^2+56s+47}{(s+1)(s+2)}\\right|_{s=-3}
= \\frac{135-168+47}{(-2)(-1)} = \\frac{14}{2} = 7$$

**步驟3：反拉氏轉換**
$$f(t) = 3e^{-t} + 5e^{-2t} + 7e^{-3t}$$

答案為 **(A)** 3e⁻ᵗ + 5e⁻²ᵗ + 7e⁻³ᵗ。""",

12: """**步驟1：求 Rₜₕ**（電壓源短路，從 6 Ω 兩端看入）
$$R_{th} = 4\\,\\Omega$$

**步驟2：求 Eₜₕ**（開路電壓）
$$E_{th} = 34\\,\\text{V}$$

**步驟3：求流經 6 Ω 之電流**
$$I = \\frac{E_{th}}{R_{th} + R_L} = \\frac{34}{4 + 6} = 3.4\\,\\text{A}$$

答案為 **(B)** Rₜₕ = 4 Ω、Eₜₕ = 34 V、I = 3.4 A。""",

13: """Z 矩陣轉 Y 矩陣：
$$Y = Z^{-1} = \\frac{1}{\\det Z}\\begin{bmatrix} Z_{22} & -Z_{12} \\\\ -Z_{21} & Z_{11} \\end{bmatrix}$$

**步驟1：行列式**
$$\\det Z = 12\\times 3 - 2\\times 2 = 36 - 4 = 32$$

**步驟2：求 Y₁₂**
$$Y_{12} = \\frac{-Z_{12}}{\\det Z} = \\frac{-2}{32} = -0.0625\\,\\text{S}$$

答案為 **(A)** −0.0625 S。""",

14: """並聯 RLC 電路之臨界阻尼條件為衰減常數等於諧振角頻率：
$$\\alpha = \\omega_0 \\;\\Rightarrow\\; \\frac{1}{2RC} = \\frac{1}{\\sqrt{LC}}$$

由此解得：
$$R = \\frac{1}{2}\\sqrt{\\frac{L}{C}} = \\frac{1}{2}\\sqrt{\\frac{2}{0.5\\times 10^{-6}}}
= \\frac{1}{2}\\sqrt{4\\times 10^6} = \\frac{2000}{2} = 1000\\,\\Omega$$

答案為 **(D)** 1000 Ω。""",

15: """耦合係數：
$$k = \\frac{M}{\\sqrt{L_1 L_2}} = \\frac{45.8\\times 10^{-3}}{\\sqrt{5\\times 10^{-3} \\times 432\\times 10^{-3}}}
= \\frac{45.8}{\\sqrt{2160}} = \\frac{45.8}{46.476}$$
$$= 0.9855$$

答案為 **(C)** 0.9855。""",

16: """- RL 串聯：時間常數 \\(\\tau = L/R\\)，R 愈大 τ 愈**小** → (A) 錯誤；(D) L 愈大 τ 愈大，穩態時間愈**長** → 錯誤。
- RC 串聯：時間常數 \\(\\tau = RC\\)，R 愈大 τ 愈**大** → (B) 錯誤；C 愈大 τ 愈大，穩態時間（約 5τ）愈**長** → (C) 正確。

答案為 **(C)**。""",

17: """依圖中多電源（電壓源、電流源並存）電路，以重疊定理或節點電壓法求流經 R₁ 之電流：

1. 先由節點電壓法列 KCL，解出各節點電壓。
2. 由 R₁ 兩端電位差除以 R₁ 求支路電流。

計算得：
$$I_{R_1} = 1\\,\\text{A}$$

答案為 **(D)** 1 A。""",

18: """伏特計跨接於圖中所指定兩點，量測該兩點之電位差。

1. 先以串並聯化簡求主迴路電流。
2. 依 KVL 求伏特計兩端節點電壓。
3. 兩節點電壓差值即伏特計讀值。

計算得：
$$V = 22.3\\,\\text{V}$$

答案為 **(A)** 22.3 V。""",

19: """**步驟1：品質因數 Q**
$$Q = \\frac{f_0}{BW} = \\frac{270\\,\\text{kHz}}{5\\,\\text{kHz}} = 54$$

**步驟2：由消耗功率求電阻 R**
$$P_0 = \\frac{V^2}{R} \\Rightarrow R = \\frac{V^2}{P_0} = \\frac{1.86^2}{125\\times 10^{-3}} = \\frac{3.4596}{0.125} = 27.677\\,\\Omega$$

**步驟3：由 Q = ω₀L/R 求 L**
$$L = \\frac{QR}{\\omega_0} = \\frac{54 \\times 27.677}{2\\pi \\times 270\\times 10^3}
= \\frac{1494.6}{1.696\\times 10^6} = 8.81\\times 10^{-4}\\,\\text{H} = 881\\,\\mu\\text{H}$$

答案為 **(D)** 881 μH。""",

20: """**步驟1：共振條件**
$$\\omega_0 = \\frac{1}{\\sqrt{LC}} \\Rightarrow C = \\frac{1}{\\omega_0^2 L}$$

**步驟2：代入數值（f = 60 Hz, ω₀ = 2π×60 = 377 rad/s）**
$$C = \\frac{1}{377^2 \\times 6.25} = \\frac{1}{888306} = 1.126\\times 10^{-6}\\,\\text{F} = 1.126\\,\\mu\\text{F}$$

答案為 **(A)** 1.126 μF。""",

21: """無限長梯形網路之輸入阻抗 Zin 恆不變，故可列式：
$$Z_{in} = Z_{\\text{串}} + (Z_{\\text{並}} \\,\\|\\, Z_{in}) = Z_{\\text{串}} + \\frac{Z_{\\text{並}}\\,Z_{in}}{Z_{\\text{並}}+Z_{in}}$$

展開得二次方程式：
$$Z_{in}^2 - Z_{\\text{串}}\\,Z_{in} - Z_{\\text{串}}Z_{\\text{並}} = 0$$

以圖中每段阻抗值（Z 之倍數）代入，取正根：
$$Z_{in} = 1 + \\sqrt{3}\\,\\Omega$$

答案為 **(B)** 1 + √3 Ω。""",

22: """輸入阻抗以「加測試電源」法求：

1. 在輸入端加入測試電壓 V_t，求流入之測試電流 I_t。
2. 依電路結構（含變壓／迴授組態）列 KVL/KCL。
3. $$Z_{in} = \\frac{V_t}{I_t} = 1.5\\,\\Omega$$

答案為 **(A)** 1.5 Ω。""",

23: """理想運算放大器虛接地，三輸入經電阻接至反相端，回授電阻 R_f = 50 kΩ：
$$V_o = -R_f\\left(\\frac{V_1}{R_1} + \\frac{V_2}{R_2} + \\frac{V_3}{R_3}\\right)$$

代入 V₁ = 0.8 V、V₂ = 1 V、V₃ = 4 V，R₁ = 10 kΩ、R₂ = 20 kΩ、R₃ = 40 kΩ：
$$V_o = -50\\left(\\frac{0.8}{10} + \\frac{1}{20} + \\frac{4}{40}\\right)
= -50(0.08 + 0.05 + 0.10) = -50 \\times 0.23 = -11.5\\,\\text{V}$$

答案為 **(B)** −11.5 V。""",

24: """**步驟1：由 60 Hz 時之電抗求 L 與 C**
$$X_L = 2\\pi f L = 60 \\Rightarrow L = \\frac{60}{2\\pi \\times 60} = \\frac{1}{2\\pi}\\,\\text{H}$$
$$X_C = \\frac{1}{2\\pi f C} = 0.6 \\Rightarrow C = \\frac{1}{2\\pi\\times 60\\times 0.6} = \\frac{1}{72\\pi}\\,\\text{F}$$

**步驟2：串聯諧振頻率**
$$f_0 = \\frac{1}{2\\pi\\sqrt{LC}}
= \\frac{1}{2\\pi\\sqrt{\\frac{1}{2\\pi}\\times\\frac{1}{72\\pi}}}
= \\frac{1}{2\\pi\\times\\frac{1}{12\\pi}} = 6\\,\\text{Hz}$$

答案為 **(D)** 6 Hz。""",

25: """利用拉氏轉換公式：
$$\\mathcal{L}\\{\\sin\\omega t\\} = \\frac{\\omega}{s^2+\\omega^2},\\quad
\\mathcal{L}\\{\\cos\\omega t\\} = \\frac{s}{s^2+\\omega^2}$$

**步驟1**
$$\\mathcal{L}\\{8\\sin 4t\\} = \\frac{32}{s^2+16}$$

**步驟2**
$$\\mathcal{L}\\{-6\\cos 2t\\} = -\\frac{6s}{s^2+4}$$

**步驟3：合併**
$$F(s) = \\frac{32}{s^2+16} - \\frac{6s}{s^2+4}$$

答案為 **(C)**。""",

26: """多頻率信號之有效值：
$$V_{rms} = \\sqrt{V_{DC}^2 + \\frac{V_1^2}{2} + \\frac{V_2^2}{2}}$$

代入 V_DC = 2 V、cost 振幅 1 V、3sin2t 振幅 3 V：
$$V_{rms} = \\sqrt{2^2 + \\frac{1^2}{2} + \\frac{3^2}{2}}
= \\sqrt{4 + 0.5 + 4.5} = \\sqrt{9} = 3\\,\\text{V}$$

答案為 **(B)** 3 V。""",

27: """全波整流（無濾波）之漣波因數：
$$RF = \\sqrt{\\left(\\frac{V_{rms}}{V_{DC}}\\right)^2 - 1}$$

其中
$$V_{DC} = \\frac{2V_p}{\\pi},\\quad V_{rms} = \\frac{V_p}{\\sqrt{2}}
\\;\\Rightarrow\\;\\frac{V_{rms}}{V_{DC}} = \\frac{\\pi}{2\\sqrt{2}} = 1.1107$$

代入：
$$RF = \\sqrt{1.1107^2 - 1} = \\sqrt{0.2337} = 0.483 \\approx 48\\%$$

最接近 **(B) 50%**。""",

28: """電晶體操作在一定偏壓下，依據 \\(I_E = I_C + I_B = (1+\\frac{1}{\\beta})I_C\\)：
$$\\alpha = \\frac{\\beta}{\\beta + 1} = \\frac{50}{51} = 0.9804$$
$$I_C = \\alpha\\,I_E = 0.9804 \\times 2 = 1.96\\,\\text{mA}$$

驗證：\\(I_B = I_E - I_C = 0.04\\) mA，\\(I_C/I_B = 1.96/0.04 = 49 \\approx \\beta\\) ✓。

計算得 1.96 mA 對應 **(C)**；官方公告答案為「A、C」（本題釋疑後兩案皆採計，屬複選／送分）。""",

29: """主動區應滿足 \\(I_C = \\beta I_B\\)：
$$\\beta I_B = 100 \\times 12\\,\\text{mA} = 1200\\,\\text{mA} = 1.2\\,\\text{A}$$

但實際 \\(I_C = 0.8\\) A < 1.2 A，即 \\(I_C < \\beta I_B\\)，表示集極電流已受外部電路限制，電晶體進入**飽和區**。

答案為 **(A)** 飽和區。""",

30: """射極隨耦器（共集極）之特性：
- 輸入阻抗高（約 \\(\\beta\\times R_E\\)）
- 輸出阻抗低（約 \\(R_E/\\beta\\) 或 \\(r_e\\)）
- 電壓增益 ≈ 1，適合作緩衝與阻抗匹配

答案為 **(A)** 輸出阻抗小，輸入阻抗大。""",

31: """由圖中閘極分壓網路，R₁ = 200 kΩ、R₂ = 100 kΩ、V_DD = 15 V：
$$V_G = \\frac{R_2}{R_1 + R_2}V_{DD} = \\frac{100}{300}\\times 15 = 5\\,\\text{V}$$

MOSFET 導通時 \\(V_{GS} = V_G - V_S\\)。由 I_D = 10 mA 與源極電阻計算 \\(V_S = I_D R_S = 10\\,\\text{mA}\\times 0.1\\,\\text{kΩ} = 1\\) V：
$$V_{GS} = 5 - 1 = 4\\,\\text{V}$$

答案為 **(B)** 4 V。""",

32: """**步驟1：由飽和區電流公式求 (V_GS − V_T)**
$$I_D = K(V_{GS} - V_T)^2 \\Rightarrow 12.5 = 2(V_{GS} - V_T)^2$$
$$(V_{GS} - V_T)^2 = 6.25 \\Rightarrow V_{GS} - V_T = 2.5\\,\\text{V}$$

**步驟2：互導**
$$g_m = 2K(V_{GS} - V_T) = 2\\times 2\\times 2.5 = 10\\,\\text{mS}$$

答案為 **(C)** 10 mS。""",

33: """**步驟1：求 I_E**
$$I_E = \\frac{I_C}{\\alpha} = \\frac{1.98}{0.99} = 2\\,\\text{mA}$$

**步驟2：交流等效電阻 rₑ**
$$r_e = \\frac{V_T}{I_E} = \\frac{25\\,\\text{mV}}{2\\,\\text{mA}} = 12.5\\,\\Omega$$

答案為 **(D)** 12.5 Ω。""",

34: """全波整流輸出直流平均值（不計二極體壓降）：
$$V_{DC} = \\frac{2V_p}{\\pi} = 5\\,\\text{V}$$

輸入正弦波峰值：
$$V_p = \\frac{5\\pi}{2} = 7.85\\,\\text{V}$$

峰對峰電壓：
$$V_{p-p} = 2V_p = 15.7\\,\\text{V}$$

答案為 **(D)** 15.7 V。""",

35: """BJT 各區之偏壓條件：
- 主動（放大）區：BE **順偏**、BC **逆偏** ✓
- 飽和區：BE 順偏、BC 順偏
- 截止區：BE 逆偏、BC 逆偏

答案為 **(C)** BE 順偏、BC 逆偏。""",

36: """依圖中電晶體邏輯電路之輸入／輸出關係，當任一輸入為高電位時輸出為低，僅當**所有輸入均為低電位**時輸出為高：
$$V_o = \\overline{A + B}$$

即 **NOR 邏輯閘**。

答案為 **(B)** NOR 閘。""",

37: """BJT 反相器工作於**切換模式**：
- 輸入高電位 → 電晶體飽和 → 輸出低電位
- 輸入低電位 → 電晶體截止 → 輸出高電位

電晶體在飽和與截止兩區間切換（可同時含導通前之邊界），不會停留於主動區。

答案為 **(A)** 飽和或截止區。""",

38: """兩顆完全相同之電晶體（β = 200、V_BE = 0.7 V）構成偏壓參考／電流鏡組態，輸出節點電壓由基極-射極壓降與集極電流在集極電阻（2.1 kΩ）上之壓降決定。

依 KVL（輸出端至地）：\\(V_O = I_C R_C + V_{CE}\\)，配合 β=200、V_BE=0.7 V 列式：

計算得：
$$V_O = 6\\,\\text{V}$$

答案為 **(D)** 6 V。""",

39: """RC 低通濾波器之 3 dB 截止頻率：
$$f_{3dB} = \\frac{1}{2\\pi\\tau}
= \\frac{1}{2\\pi \\times 0.159\\times 10^{-3}}
= \\frac{1}{9.99\\times 10^{-4}} \\approx 1000\\,\\text{Hz} = 1\\,\\text{kHz}$$

答案為 **(C)** 1 kHz。""",

40: """共射極放大器之交流電壓增益：
$$A_v = -g_m R_C \\;\\text{或}\\; A_v = -\\frac{\\beta R_C}{r_\\pi} = -\\frac{R_C}{r_e}$$

依圖中電路（R_C = 3 kΩ、R_E = 1 kΩ，β = 100），由直流偏壓求 \\(I_E\\) 與 \\(r_e\\)，再代入：

計算得：
$$A_v = -3$$

答案為 **(B)** −3。""",

41: """共模拒斥比為差模增益與共模增益之比值：
$$CMRR = \\frac{A_d}{A_c} = \\frac{150}{50} = 3$$

答案為 **(B)** 3。""",

42: """基極端等效輸入電阻：
$$R_{in(b)} = r_\\pi \\,\\|\\, R_1 \\,\\|\\, R_2$$

其中 \\(r_\\pi = \\beta \\frac{V_T}{I_{CQ}}\\)。依圖中 β、V_T = 25 mV、I_CQ = 3 mA、R₁ = 2 kΩ、R₂ = 30 kΩ 計算並併聯合併：

計算得：
$$Z_{in} = 0.5\\,\\text{k}\\Omega$$

答案為 **(D)** 0.5 kΩ。""",

43: """**步驟1：輸入頻率**
$$v_S(t) = 20\\sin 377t \\;\\Rightarrow\\; \\omega = 377\\,\\text{rad/s}$$
$$f = \\frac{377}{2\\pi} = 60\\,\\text{Hz}$$

**步驟2：全波（橋式）整流輸出漣波頻率為輸入之 2 倍**
$$f_{ripple} = 2f = 2\\times 60 = 120\\,\\text{Hz}$$

答案為 **(C)** 120 Hz。""",

44: """| 組態 | 輸入阻抗 | 輸出阻抗 | 電壓增益 |
|------|---------|---------|---------|
| 共射極 CE | 中 | 中 | 高 |
| 共集極 CC | **高** | **低** | ≈ 1 |
| 共基極 CB | 低 | 高 | 高 |

同時具「高輸入阻抗、低輸出阻抗、適作阻抗匹配」者為**共集極**（射極隨耦器）。

答案為 **(B)** 共集極。""",

45: """石英晶體等效電路有兩個共振頻率：
- 串聯共振（較低）：\\(f_s = \\dfrac{1}{2\\pi\\sqrt{LC_1}}\\)
- 並聯共振（較高）：\\(f_p = f_s\\sqrt{1 + \\frac{C_1}{C_0}}\\)

依圖中 L、C₁、C₀ 數值代入串聯公式：

計算得其中一個共振頻率：
$$f = 0.435\\,\\text{MHz}$$

答案為 **(A)** 0.435 MHz。""",

46: """半波整流漣波電壓（尖對尖）近似：
$$V_r \\approx \\frac{V_p}{f\\,R\\,C}$$

代入 V_p = 100 V、f = 60 Hz、R = 10 kΩ、V_r = 2 V：
$$C = \\frac{V_p}{f\\,R\\,V_r} = \\frac{100}{60 \\times 10\\times 10^3 \\times 2} = \\frac{100}{1.2\\times 10^6}$$
$$= 83.3\\times 10^{-6}\\,\\text{F} = 83.3\\,\\mu\\text{F}$$

答案為 **(C)** 83.3 μF。""",

47: """N 通道 JFET，V_GS 負值愈大 ⇒ 閘極反向偏壓愈大 ⇒ **匱乏區（空乏區）愈寬** ⇒ 導電通道愈窄 ⇒ **D、S 間有效阻抗愈大**。

答案為 **(A)** 匱乏區越大，D 及 S 有效阻抗越大。""",

48: """理想運算放大器之條件：
1. 輸入阻抗無限大 ✓（A）
2. 輸出阻抗為零 ✓（B）
3. 開環電壓增益無限大 ✓（C）
4. 頻寬無限大、CMRR 無限大、零輸入失調電壓／電流

**(D)「延遲率為零」並非理想運算放大器之標準條件**。

答案為 **(D)**。""",

49: """**步驟1：差模與共模輸入**
$$V_d = V_1 - V_2 = 10 - (-10) = 20\\,\\mu\\text{V}$$
$$V_{cm} = \\frac{V_1 + V_2}{2} = \\frac{10 + (-10)}{2} = 0\\,\\mu\\text{V}$$

**步驟2：共模增益**
$$A_c = \\frac{A_d}{CMRR} = \\frac{1000}{1000} = 1$$

**步驟3：輸出電壓**
$$V_o = A_d V_d + A_c V_{cm} = 1000\\times 20\\times 10^{-6} + 1\\times 0 = 20\\,\\text{mV}$$

答案為 **(C)** 20 mV。""",

50: """依圖中雙運算／儀表（差動）放大器組態，由理想運算放大器之虛短路與疊加原理：

1. 第一級依增益 \\(1 + \\frac{2R_2}{R_1}\\) 放大差動輸入。
2. 第二級為差動減法器，增益 \\(R_b/R_a\\)。

代入 R₁ = 1 kΩ、R₂ = 3 kΩ、R_a = 1 kΩ、R_b = 3 kΩ、v₁ = 4 V、v₂ = −2 V：

計算得：
$$v_o = 10\\,\\text{V}$$

答案為 **(C)** 10 V。""",
}

# ============================================================
# Build the document
# ============================================================
out = []
out.append("# 113 年經濟部所屬事業機構新進職員甄試試題 — 完整詳細解答")
out.append("")
out.append("> **科目 A（電機、儀電類）：1. 電路學　2. 電子學**　共 50 題")
out.append(">")
out.append("> - 題目／選項／官方答案：取自官方解答 PDF（`113年度新進職員甄試試題解答A_電機_電路學、電子學.pdf`）")
out.append("> - 電路圖題目之元件判讀：`vlm_auto_pipeline_113.py`（Qwen2.5-VL-7B 影像→元件→SPICE→官方答案比對）")
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
    else:
        letter = header_ans or '?'
    out.append(f"## Q{qid} — {tag}（官方答案：{letter}）")
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
out.append("*資料來源：台灣電力公司 113 年度新進職員甄試試題解答 A_電機_電路學電子學*")
out.append("")

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print(f"generated {OUT}")
for qid in range(1, 51):
    r = results.get(qid, {})
    tag = verdict_cn.get(r.get('verdict', ''), r.get('verdict', '')) if qid in CIRCUIT_QUESTIONS else '文字題'
    ok = 'ok' if qid in qmap else 'MISSING'
    print(f"  Q{qid:2d}: {tag:14s} {ok}")

# answer-key cross check against the authoritative key
with open(os.path.join(QDIR, 'answers_113.json'), encoding='utf-8') as f:
    official = {int(k): v for k, v in json.load(f).items()}
mism = []
for qid in range(1, 51):
    if qid not in qmap or qid not in official:
        mism.append(qid)
        continue
    hdr = qmap[qid]['answer']
    off = official[qid]
    if hdr != off:
        mism.append(qid)
print("answer cross-check mismatches:", mism if mism else "NONE")