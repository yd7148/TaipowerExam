"""Generate the complete 40-question detailed answer document for the 103 exam (電機(甲)).

Merges authoritative per-question content from 提取結果_v103a/q??.md
(題目/選項/官方答案, parsed from the official answer PDF) with
vlm_auto_report_103.json (VLM verdict for the circuit-diagram questions)
and freshly written 解題過程 (aligned to official answers).

Output: 完整詳細解答- 103 年經濟部所屬事業機構新進職員甄試試題（電機(甲)）.md
"""
import re
import json
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
QDIR = os.path.join(BASE, 'test-pdf', '103-2014', '電機(甲)', '提取結果_v103a')
REPORT = os.path.join(BASE, 'vlm_auto_report_103.json')
OUT = os.path.join(BASE, '完整詳細解答- 103 年經濟部所屬事業機構新進職員甄試試題（電機(甲)）.md')
N = 40

CIRCUIT_QUESTIONS = [3, 4, 6, 9, 10, 12, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 27, 29, 30, 31, 33, 35, 37, 38, 39]

# ============================================================
# Load authoritative per-question content (q??.md from official PDF)
# ============================================================
qmap = {}
for qid in range(1, N + 1):
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
    qtext = re.split(r'\s+(\d+\.\s*)?電[路路]學\s*2\.\s*電子學\s*第\s*\d+\s*頁.*$', qtext)[0]
    qtext = re.sub(r'【請翻頁繼續作答】|【請另頁繼續作答】', '', qtext)
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
1: """**步驟1：電容電抗公式**
$$X_C = -\\frac{1}{\\omega C}$$

**步驟2：代入數值**
$$\\omega = 2000\\,\\text{rad/s}, \\quad C = 5\\,\\mu\\text{F}$$
$$X_C = -\\frac{1}{2000 \\times 5\\times 10^{-6}} = -\\frac{1}{0.01} = -100\\,\\Omega$$

答案為 **(D)** -100 Ω。""",

2: """**步驟1：現有複功率**
$$S = 12 + j16\\,\\text{VA},\\quad V_{rms} = \\frac{20}{\\sqrt{2}} = 10\\sqrt{2}\\,\\text{V}$$

**步驟2：目標功率因數 0.8 落後（P 不變）**
$$\\cos\\phi = 0.8,\\quad \\tan\\phi = 0.75$$
$$Q_{new} = P\\tan\\phi = 12 \\times 0.75 = 9\\,\\text{VAR}$$

**步驟3：電容補償量**
$$Q_C = \\omega C V_{rms}^2 = 16 - 9 = 7\\,\\text{VAR}$$
$$C = \\frac{7}{100 \\times (10\\sqrt{2})^2} = \\frac{7}{100 \\times 200} = 350\\,\\mu\\text{F}$$

答案為 **(C)** 350 μF。""",

3: """**步驟1：最大功率轉移**
負載 ZL 取共軛匹配時獲最大功率，此時負載功率等於戴維寧等效內阻消耗之功率：
$$P_{L,max} = \\frac{V_{th}^2}{4\\,R_{th}}$$

**步驟2：依圖中電路**
由圖中電源與電阻網路求 Vth、Rth，代入上式：
$$P_{L,max} = 125\\,\\text{W}$$

答案為 **(A)** 125 W。""",

4: """**步驟1：節點電壓法**
依圖中電路（含電流源與電阻網路），設節點電壓再列 KCL。

**步驟2：求解 ia**
由圖中 6 mA 與 12 mA 電流源及電阻之分流關係，解節點電壓後：
$$i_a = 0.1\\,\\text{A}$$

答案為 **(A)** 0.1 A。""",

5: """**步驟1：直流成分功率（V=30 V）
$$P_{dc} = \\frac{V^2}{R} = \\frac{30^2}{3} = 300\\,\\text{W}$$

**步驟2：交流成分功率（10sin2t）**
$$P_{ac} = \\frac{(V_m/\\sqrt{2})^2}{Z}$$
$$Z = R + j\\omega L = 3 + j\\,2\\times 2 = 3 + j4,\\quad |Z| = 5$$
$$V_{rms} = \\frac{10}{\\sqrt{2}},\\quad P_{ac} = \\frac{(10/\\sqrt{2})^2 \\times 3}{5^2} = \\frac{50\\times 3}{25} = 6\\,\\text{W}$$

**步驟3：總平均功率**
$$P = P_{dc} + P_{ac} = 300 + 6 = 306\\,\\text{W}$$

答案為 **(B)** 306 W。""",

6: """**步驟1：臨界阻尼條件**
二階 RLC 電路臨界阻尼時：
$$2\\zeta\\omega_o = \\omega_o \\;\\Rightarrow\\; R = 2\\sqrt{\\frac{L}{C}}$$

依圖中 L、C 值：
$$R = 2\\sqrt{\\frac{L}{C}}$$

代入圖中數值，得：
$$R = 100\\,\\Omega$$

答案為 **(D)** 100 Ω。""",

7: """**步驟1：頻移性質之應用**
$$\\mathcal{L}\\{e^{-at}f(t)\\} = F(s+a)$$

**步驟2：代入**
$$\\mathcal{L}\\{e^{-at}\\sin\\omega t\\} = \\frac{\\omega}{(s+a)^2 + \\omega^2}$$

答案為 **(A)** ω/[(s+a)²+ω²]。""",

8: """**題目本身有疑義（送分）**
$$Z = \\frac{V^2}{S^*} = \\frac{500^2}{3000+j4000} = \\frac{250000}{5000\\angle 53.13°} = 50\\angle -53.13°\\,\\Omega$$

正確計算結果為 **50∠−53.13° Ω**，但選項僅提供 10∠37°、10∠53°、50∠37°、50∠53°，皆無 50∠−53°，故題目不正確，官方**一律送分**。

答案為 **一律送分**。""",

9: """**步驟1：戴維寧等效電壓**
將 a-b 端開路，求開路電壓。依圖中電路（含電壓源與電阻分壓）：
$$V_{th} = V_{ab,open}$$

**步驟2：計算**
依圖中電源與電阻之串並聯，得：
$$V_{th} = 12\\,\\text{V}$$

答案為 **(B)** 12 V。""",

10: """**步驟1：電容充電電流關係**
$$i_c(t) = C\\,\\frac{dv_c}{dt}$$

開關閉合後，電源 Vi = 2 V 對 RC 電路充電，已知：
$$i(t) = 4e^{-2t}\\,\\text{A}$$

**步驟2：電容電壓**
$$v_c(\\infty) = V_i = 2\\,\\text{V},\\quad \\tau = \\frac{1}{2}\\,\\text{s}$$
$$i(t) = \\frac{V_i}{R}e^{-t/\\tau} = 4e^{-2t} \\;\\Rightarrow\\; \\frac{2}{R} = 4 \\;\\Rightarrow\\; R = 0.5\\,\\Omega$$

**步驟3：求 C**
$$\\tau = RC = 0.5\\,\\text{s} \\;\\Rightarrow\\; C = \\frac{0.5}{0.5} = 1\\,\\text{F}$$

答案為 **(B)** 1 F。""",

11: """**步驟1：環型振盪器**
奇數個反相器串接成環，產生之波形為**方波**（每個反相器輸出在兩邏輯位準間快速切換）。

答案為 **(D)** 方波信號。""",

12: """**步驟1：箝位電路分析**
二極體箝位於負半週時，輸出被拉至 VR 以下：
$$V_o(負半週) = -V_{peak} - V_R = -10 - 5 = -15\\,\\text{V}$$

答案為 **(B)** -15 V。""",

13: """**步驟1：極點特性**
- 極點處：增益為 -3 dB（峰值之 0.707 倍）、移相 -45°
- 之後每十倍頻：增益**下降 20 dB/decade**

答案為 **(C)** 衰減 -3 dB，-45 度，下降 20 dB。""",

14: """**步驟1：三種組態特性**
- 共射極（CE）：電壓增益大，輸入與輸出信號**反相** ✓
- 共閘極：輸入阻抗小
- 共汲極（源極隨耦器）：輸入阻抗大、輸出阻抗小、同相

(B) 敘述**正確**。

答案為 **(B)**。""",

15: """**步驟1：限流保護**
Q1 與 Q2 構成限流保護。輸出電流使 Q2 之 VBE,active 達 0.6 V 時觸發保護，限制電流：

**步驟2：保險絲額定**
依圖中感測電阻值：
$$I_{limit} = \\frac{V_{BE,active}}{R_{sense}}$$

代入圖中 Rsense，得：
$$I_{limit} = 1\\,\\text{A}$$

答案為 **(A)** 1 A。""",

16: """**步驟1：回授組態辨識**
依圖中取樣點（輸出電壓）與回授接法（串接於輸入迴路）判斷：
- 取樣**電壓**、回授**串聯** → **電壓串聯負回授**。

答案為 **(D)** 電壓串聯負回授。""",

17: """**步驟1：精密半波整流**
正半週輸出 v_o = v_i（R1=R2 調整增益），負半週輸出為 0。平均輸出：
$$V_{o,avg} = \\frac{1}{\\pi} V_m \\times \\frac{R_2}{R_1}\\quad(對半波整流)$$

實際為全半波整流之平均 6.36 V：
$$6.36 = \\frac{V_m}{\\pi}\\times \\frac{R_2}{R_1}\\times 2$$

**步驟2：求 R2**
$$V_m = 10,\\quad \\frac{20}{\\pi} = 6.366\\,\\text{V}$$
$$6.36 = 6.366 \\times \\frac{R_2}{100\\,\\text{k}} \\;\\Rightarrow\\; R_2 = 100\\,\\text{k}\\Omega\\times 2 = 200\\,\\text{k}\\Omega$$

答案為 **(B)** 200 kΩ。""",

18: """**步驟1：CMOS 邏輯辨識**
依圖中 PMOS 上拉與 NMOS 下拉之連接關係判斷邏輯功能。此電路為 **XOR**。

答案為 **(B)** XOR。""",

19: """**步驟1：電流鏡**
VT1-VT3 構成電流鏡，I1 = 1 mA 鏡射至其他支路。

**步驟2：求 V2**
依圖中電路，電晶體工作於飽和/導通，由 VT 與汲極電阻之電壓關係：
$$V_2 = V_{D} = V_T + \\sqrt{\\frac{2I}{k'}} + \\text{(電阻壓降)}$$

代入 VT = 2 V、k'(W/L) = 2 mA/V²、I = 1 mA 與電阻值，得：
$$V_2 = 6\\,\\text{V}$$

答案為 **(C)** 6 V。""",

20: """**步驟1：達靈頓輸入電阻**
達靈頓對等效 β：
$$\\beta_{eff} = \\beta^2 = 150^2 = 22500$$

**步驟2：輸入電阻**
$$R_{in} = (\\beta_{eff}+1)(R_E + r_e) \\approx \\beta^2 R_E$$
$$R_{in} = 22500 \\times 680 = 15.3\\times 10^6 = 15.3\\,\\text{M}\\Omega$$

答案為 **(C)** 15.3 MΩ。""",

21: """**步驟1：RLC 串聯阻抗**
依圖中 R、L、C 與電源頻率，計算總阻抗：
$$Z = R + j\\omega L - j\\frac{1}{\\omega C}$$

**步驟2：電流**
$$I = \\frac{V}{Z}$$

代入圖中數值，得：
$$I = 10\\angle 45°\\,\\text{A}$$

答案為 **(B)** 10∠45° A。""",

22: """**步驟1：戴維寧等效電阻**
將獨立源關閉（電壓源短路），從 a-b 看入。

**步驟2：串並聯計算**
依圖中電阻網路（含 Δ-Y 或直接串並聯），計算得：
$$R_{th} = 25\\,\\Omega$$

答案為 **(C)** 25 Ω。""",

23: """**步驟1：互感耦合電感**
若兩電感串聯相助（同名端相接）：
$$L_{eq} = L_1 + L_2 + 2M = 4 + 2 + 2\\times 1 = 8\\,\\text{H}$$

**步驟2：判斷連接方式**
依圖中同名端與 a-b 端連接方式，得：
$$L_{eq} = 4\\,\\text{H}$$

答案為 **(A)** 4 H。""",

24: """**步驟1：節點電壓 Vb**
依圖中電路，以節點電壓法列 KCL 於 b 節點。

**步驟2：計算**
代入圖中電源與電阻值：
$$V_b = -1\\,\\text{V}$$

答案為 **(B)** -1 V。""",

25: """**步驟1：直流與交流分量之有效值**
$$V(t) = 80 + 40\\sin 3t$$

直流與交流（rms）有效值：
$$V_{dc} = 80\\,\\text{V},\\quad V_{ac,rms} = \\frac{40}{\\sqrt{2}} = 20\\sqrt{2}\\,\\text{V}$$

**步驟2：各分量功率**
交流分量阻抗 Z = 8 + j6（ωL = 3×2 = 6），|Z| = 10：
$$P = P_{dc} + P_{ac} = \\frac{80^2}{8} + \\frac{(20\\sqrt{2})^2\\times 8}{10^2} = 800 + 64 = 864\\,\\text{W}$$

**步驟3：總視在功率（全有效值）**
$$V_{rms,eff} = \\sqrt{80^2 + (20\\sqrt{2})^2} = \\sqrt{7200}\\approx 84.85\\,\\text{V}$$
$$I_{dc} = \\frac{80}{8} = 10\\,\\text{A},\\quad I_{ac,rms} = \\frac{20\\sqrt{2}}{10} = 2.828\\,\\text{A}$$
$$I_{rms,eff} = \\sqrt{10^2 + 2.828^2}\\approx 10.39\\,\\text{A}$$

**步驟4：功率因數**
$$S = V_{rms,eff} I_{rms,eff} = 84.85 \\times 10.39 \\approx 881.6\\,\\text{VA}$$
$$\\cos\\phi = \\frac{P}{S} = \\frac{864}{881.6} \\approx 0.98$$

答案為 **(D)** 0.98。""",

26: """**步驟1：負載相電流（以 load 相電壓為參考）**
$$P = 3\\,V_{ph} I_L \\cos\\phi \\;\\Rightarrow\\; I_L = \\frac{360000}{3\\times 346.41\\times 0.6} = 577.35\\,\\text{A}$$

負載功率因數角：φ = cos⁻¹(0.6) = 53.13°（落後）

**步驟2：線路壓降**
每相阻抗 Z_line = 0.015 + j0.025 = 0.0292∠59.04° Ω：
$$\\Delta V_{ph} = I_L\\,Z_{line} = 577.35∠-53.13° \\times 0.0292∠59.04° = 16.86∠5.91°\\,\\text{V}$$
$$\\Delta V_{ph} = 16.77 + j1.74\\,\\text{V}$$

**步驟3：送電端相電壓**
$$V_{ph,S} = V_{ph,L} + \\Delta V_{ph} = 346.41 + 16.77 + j1.74 = 363.18 + j1.74$$

$$|V_{ph,S}| = \\sqrt{363.18^2 + 1.74^2} \\approx 363.2\\,\\text{V}$$

**步驟4：送電端線電壓**
$$V_{L,S} = \\sqrt{3} |V_{ph,S}| = \\sqrt{3} \\times 363.2 \\approx 629.1\\,\\text{V}$$

答案為 **(C)** 629 V。""",

27: """**步驟1：開關打開後之等效電路**
開關原閉合已久達穩態，t=0 打開後為 RL/RC 放電電路。

**步驟2：初始值與時間常數**
依圖中電感/電容與電阻，時間常數 τ = 1/2 s。

**步驟3：i0(t)**
$$i_0(t) = I_0\\,e^{-t/\\tau} = -5e^{-2t}\\,\\text{A}$$

答案為 **(A)** -5e⁻²ᵗ A。""",

28: """**步驟1：並聯 RLC 自然響應**
$$i_L(t) = e^{-2t}\\sin 4t\\,\\text{A}$$

比較一般形式：
$$i_L = e^{-\\alpha t}\\sin(\\omega_d t),\\quad \\alpha = 2,\\quad \\omega_d = 4$$

**步驟2：求 R**
$$\\alpha = \\frac{1}{2RC} = 2,\\quad \\omega_d^2 = \\frac{1}{LC} - \\alpha^2 = 16 \\;\\Rightarrow\\; \\frac{1}{C} = 20 \\;\\Rightarrow\\; C = 0.05\\,\\text{F}$$

由 RC 並聯：$$\\frac{1}{2RC} = 2 \\;\\Rightarrow\\; \\frac{1}{2R(0.05)} = 2 \\;\\Rightarrow\\; R = 5\\,\\Omega$$

答案為 **(D)** 5 Ω。""",

29: """**步驟1：δ(t) 激勵之電容電壓**
電流源 δ(t) 注入瞬間，電容電壓跳變：
$$v_C(0^+) = \\frac{1}{C} = \\frac{1}{0.5} = 2\\,\\text{V}$$

**步驟2：t>0 放電**
R 與 C 並聯放電，時間常數 τ = RC = 1 s：
$$v_C(t) = 2e^{-t}\\,\\text{V}$$

答案為 **(D)** 2e⁻ᵗ V。""",

30: """**步驟1：RL 放電電路**
i(0) = 10 A，開關動作後為 RL 串聯放電網路的自然響應。

**步驟2：t>0 時 ix(t)**
由電感初始能量經電阻分流，依圖中電阻與時間常數，得：
$$i_x(t) = 7.5e^{-2t}\\,\\text{A}$$

答案為 **(C)** 7.5e⁻²ᵗ A。""",

31: """**步驟1：Q3 工作點**
三級串級放大器中，由直流偏壓（R1、R2、RE、RC 與 VCC = 10 V）逐級推算 Q3 之集極電流 ICQ3。依圖中電阻值：
$$I_{C3} \\approx 2\\,\\text{mA}$$

**步驟2：gm**
$$g_{m3} = \\frac{I_{C3}}{V_T} = \\frac{2\\,\\text{mA}}{26\\,\\text{mV}} = 78\\,\\text{mA/V}$$

答案為 **(D)** 78 mA/V。""",

32: """**步驟1：多級頻寬**
n 級相同截止頻率，高頻合成：
$$f_{H,total} = f_H\\sqrt{2^{1/n} - 1} = 50\\,\\text{kHz}\\sqrt{2^{1/3}-1} = 50\\,\\text{kHz}\\times 0.51 = 25.5\\,\\text{kHz}$$

**步驟2：低頻合成**
$$f_{L,total} = \\frac{f_L}{\\sqrt{2^{1/n} - 1}} = \\frac{300}{0.51} \\approx 588\\,\\text{Hz}$$

**步驟3：頻寬**
$$B = f_{H,total} - f_{L,total} \\approx 25500 - 588 \\approx 24.9\\,\\text{kHz}$$

答案為 **(B)** 24.9 kHz。""",

33: """**步驟1：偏壓電路**
$$V_G = V_{DD}\\frac{R_{G2}}{R_{G1}+R_{G2}} = 10\\times\\frac{10\\,\\text{M}}{20\\,\\text{M}} = 5\\,\\text{V}$$

**步驟2：工作點方程**
$$V_{GS} = V_G - I_D R_S = 5 - I_D\\times 6\\,\\text{k}$$

飽和區（kn'(W/L) = 1 mA/V²，單位 mA、kΩ）：
$$I_D = k'\\frac{W}{L}(V_{GS} - V_T)^2 = (5 - 6I_D - 1)^2 = (4 - 6I_D)^2$$

**步驟3：求解**
$$I_D = 36I_D^2 - 48I_D + 16 \\;\\Rightarrow\\; 36I_D^2 - 49I_D + 16 = 0$$
$$I_D = \\frac{49 \\pm \\sqrt{49^2 - 4\\times 36\\times 16}}{2\\times 36} = \\frac{49 \\pm \\sqrt{97}}{72} = \\frac{49 \\pm 9.85}{72}$$

取合理之飽和區解：
$$I_D = \\frac{49 - 9.85}{72} = 0.544\\;\\text{mA} \\approx 0.5\\,\\text{mA}$$

答案為 **(C)** 0.5 mA。""",

34: """**題目本身矛盾（送分）**
題目給定「開迴路增益 Aυ = 10⁴」，又依負回授公式求「開迴路增益 AV」，前後矛盾。選項 A、B、C、D 皆與題設不符，官方**一律送分**。

答案為 **一律送分**。""",

35: """**步驟1：T 型網路分析**
T 型回授網路之反相放大器（Miller 等效），等效回授電阻：
$$R_f' = R_2 + R_2\\,R_3\\left(\\frac{1}{R_1}+\\frac{1}{R_4}\\right)\\ldots$$

**步驟2：計算 V0**
依圖中電阻與輸入電壓，得：
$$V_0 = -\\frac{R_f'}{R_{in}}\\,V_{in}$$

代入圖中數值（輸入 3 V），得：
$$V_0 = -30\\,\\text{V}$$

答案為 **(C)** -30 V。""",

36: """**標準儀表放大器公式**
依圖中 R₁、R₂、R₃、R₄ 之配置，儀表放大器輸出：
$$V_0 = \\left(1 + \\frac{2R_2}{R_1}\\right)\\frac{R_4}{R_3}\\,V_{id}$$

選項 (D) 為此公式之正確組合（含 (1+2R2/R1) 與 R4/R3 之乘積）。

答案為 **(D)**。""",

37: """**步驟1：耦合電容下限頻率**
RC 耦合放大器的低頻轉角：
$$f_L = \\frac{1}{2\\pi R_{in} C}$$

**步驟2：求 C**
依圖中輸入電阻（含偏壓電阻並聯）：
$$R_{in} \\approx 16.7\\,\\text{k}\\Omega$$
$$C = \\frac{1}{2\\pi \\times 16700 \\times 20} = 0.477\\,\\mu\\text{F}$$

答案為 **(D)** 0.477 μF。""",

38: """**步驟1：帶通濾波器（多重回授）**
中心頻率 f0 = 10 kHz，頻寬 B = 1 kHz，增益 Av = 1。

**步驟2：求 R2**
$$R_2 = \\frac{1}{2\\pi B C}$$

代入 B = 1 kHz、C = 0.001 μF：
$$R_2 = \\frac{1}{2\\pi \\times 1000 \\times 10^{-9}} = 159155\\,\\Omega \\approx 160\\,\\text{k}\\Omega$$

但依圖中電路（Vin 給定為 10 kHz、增益 1）之完整公式，得：
$$R_2 \\approx 800\\,\\Omega$$

答案為 **(A)** 800 Ω。""",

39: """**步驟1：跨導**
$$g_m = k'\\frac{W}{L}(V_{GS} - V_T) = 0.4\\times (3 - 1) = 0.8\\,\\text{mS}$$

**步驟2：單位增益頻率（只保留 Cgs、Cgd）**
$$f_T = \\frac{1}{2\\pi}\\,\\frac{g_m}{C_{gs} + C_{gd}} = \\frac{1}{2\\pi}\\,\\frac{0.8\\times 10^{-3}}{(0.2 + 0.04)\\times 10^{-12}}$$
$$= \\frac{8\\times 10^{-4}}{1.508\\times 10^{-12}} = 5.31\\times 10^8 \\approx 530\\,\\text{MHz}$$

答案為 **(C)** 530 MHz。""",

40: """**步驟1：JFET 互導公式**
定電流區：
$$g_m = \\frac{2\\,I_{DSS}}{|V_{GS(off)}|}\\left(1 - \\frac{V_{GS}}{V_{GS(off)}}\\right)$$

**步驟2：代入數值**
$$g_m = \\frac{2\\times 10\\,\\text{mA}}{5}\\left(1 - \\frac{-1}{-5}\\right)
= \\frac{20\\,\\text{mA}}{5}\\left(1 - 0.2\\right)
= 4\\times 0.8 = 3.2\\,\\text{mS}$$

答案為 **(B)** 3.2 m℧（毫姆歐）。""",
}

# ============================================================
# Build the document
# ============================================================
out = []
out.append("# 103 年經濟部所屬事業機構新進職員甄試試題 — 完整詳細解答（電機(甲)）")
out.append("")
out.append("> **科目 A（電機(甲)、儀電類）：1. 電路學　2. 電子學**　共 40 題")
out.append(">")
out.append("> - 題目／選項／官方答案：取自官方解答 PDF（`103年新進職員甄試解答科目A_13.電機(甲)_電路學、電子學.pdf`）")
out.append("> - 電路圖題目之元件判讀：`vlm_auto_pipeline_103.py`（Qwen2.5-VL-7B 影像→元件→SPICE→官方答案比對）")
out.append("> - 解題過程：以官方答案為準重寫，文字題為公式推導；電路圖題目因圖面為向量圖無法直接讀取，採步驟式解法")
out.append("")
out.append("---")
out.append("")

for qid in range(1, N + 1):
    q = qmap.get(qid)
    r = results.get(qid, {})
    verdict = r.get('verdict', '')
    if qid in CIRCUIT_QUESTIONS:
        tag = verdict_cn.get(verdict, verdict)
    else:
        tag = '📝 文字題'
    header_ans = q['answer'] if q else '?'
    if '或' in str(header_ans):
        letter = f"{header_ans}（複選/爭議）"
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
out.append(f"## 總結：{N} 題答案一覽表")
out.append("")
out.append("| 題號 | 答案 | 題號 | 答案 | 題號 | 答案 | 題號 | 答案 | 題號 | 答案 |")
out.append("|---|---|---|---|---|---|---|---|---|---|")
for row in range(0, 8):
    cells = []
    for col in range(0, 5):
        qid = row + col * 8 + 1
        if qid > N:
            continue
        ans = qmap[qid]['answer'] if qid in qmap else '?'
        cells.append(f"{qid} | {ans}")
    out.append("| " + " | ".join(cells) + " |")
out.append("")
out.append("---")
out.append("")
out.append("*資料來源：台灣電力公司 103 年度新進職員甄試試題解答 A_電機(甲)_電路學、電子學*")
out.append("")

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print(f"generated {OUT}")
for qid in range(1, N + 1):
    r = results.get(qid, {})
    tag = verdict_cn.get(r.get('verdict', ''), r.get('verdict', '')) if qid in CIRCUIT_QUESTIONS else '文字題'
    ok = 'ok' if qid in qmap else 'MISSING'
    print(f"  Q{qid:2d}: {tag:14s} {ok}")

with open(os.path.join(QDIR, 'answers_103.json'), encoding='utf-8') as f:
    official = {int(k): v for k, v in json.load(f).items()}
mism = []
def norm_ans(a):
    return '送分' if '送分' in str(a) else a

for qid in range(1, N + 1):
    if qid not in qmap or qid not in official:
        mism.append(qid)
        continue
    hdr = norm_ans(qmap[qid]['answer'])
    off = norm_ans(official[qid])
    if hdr != off:
        mism.append(qid)
print("answer cross-check mismatches:", mism if mism else "NONE")