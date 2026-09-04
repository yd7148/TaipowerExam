# 國營事業招考試題處理專案

## 目的
擷取國營事業（台電、中油、台水、台糖等）招考試題 PDF，進行 OCR 文字辨識、題目拆分、網路搜尋官方解答，並產出含完整解題過程的詳細解答檔。

## 目錄結構

```
test-pdf/
├── 114-2025/
│   ├── 電機/
│   │   ├── 114年度...科目A_電機_電路學電子學.pdf     # 試題 PDF
│   │   ├── 114年度...解答A_電機_電路學電子學.pdf     # 解答 PDF
│   │   ├── 114年度...科目B_電機_電力系統_電機機械.pdf
│   │   ├── 114年度...解答B_電機_電力系統_電機機械.pdf
│   │   └── 提取結果_v4/
│   │       ├── q01.md ~ q50.md                       # 逐題 OCR 文字
│   │       ├── q01.png ~ q50.png                     # 逐題裁切圖片
│   │       ├── exam_page1.png ~ exam_page4.png        # 試題整頁渲染
│   │       ├── answer_page1.png ~ answer_page4.png    # 解答整頁渲染
│   │       └── 完整解答.md                            # 含詳細過程的完整解答
│   └── 儀電/
│       └── ...
└── README.md                                          # 本說明檔
```

## 已完成

### 114年度（2025年）電機類
- 科目A：電路學電子學（50題）— ✅ 完整解答含解題過程
- 科目B：電力系統電機機械 — PDF 已下載，待處理

## PDF 來源

### 官方網站
台灣電力公司 114 年度新進職員甄試試題與解答公告頁面：
`https://www.taipower.com.tw/2289/2544/2554/2556/simpleList`

### 直接下載連結（需確認時效性）
- **科目A 試題**：`https://www.taipower.com.tw/media/yz3ciujc/114年度新進職員甄試試題科目A_電機_電路學電子學.pdf?mediaDL=true`
- **科目A 解答**：`https://www.taipower.com.tw/media/mxkce0zb/114年度新進職員甄試試題解答A_電機_電路學電子學.pdf?mediaDL=true`

### 其他管道
| 來源 | 網址 | 備註 |
|------|------|------|
| 阿摩線上測驗 | `https://yamol.tw/` | 有題目文字，部分有解答 |
| 百官網公職 | `https://byone.tkb.com.tw/downloads/` | 有考古題下載 |
| 公職王 | `https://www.public.com.tw/exampoint/` | 有歷屆試題 |
| Scribd | `site:scribd.com` 搜尋 | 有部分上傳試題 |

## 使用方法

### 安裝相依套件
```bash
pip install pymupdf Pillow pytesseract
```

### 從 PDF 擷取題目
```python
import fitz  # pymupdf

doc = fitz.open("路徑/試題.pdf")
for page_num in range(len(doc)):
    page = doc[page_num]
    # 整頁渲染
    mat = fitz.Matrix(3, 3)
    pix = page.get_pixmap(matrix=mat)
    pix.save(f"exam_page{page_num+1}.png")
    # 文字擷取
    text = page.get_text()
    print(text)
```

### 從解答 PDF 提取答案
```python
doc = fitz.open("路徑/解答.pdf")
for page in doc:
    print(page.get_text())
```
答案格式：`[X]` 為各題答案（X = A/B/C/D）

## 重要限制
- pymupdf **無法擷取向量圖形**（電路圖的線路連接），僅能取得元件標註文字
- 加密 PDF 需提供密碼才能開啟
- OCR 對中文 + 數學符號的辨識率有限，需交叉比對
- 圖片辨識需依賴模型的圖片處理能力（目前模型不支援直接讀取圖片）

## 相關模型
- 科目A（電機類）：50 題，2 分/題，90 分鐘
- 科目B（電機類）：50 題，2 分/題，90 分鐘
- 及格標準：依當次考試公告
