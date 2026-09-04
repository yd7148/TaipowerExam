# PDF 考題擷取與 OCR 辨識說明

## 概述

本文件說明如何從考題 PDF 檔案中，自動擷取每個題目為獨立的圖片，並進行 OCR 文字辨識。

## 所需套件

```bash
pip install pymupdf pdfplumber easyocr opencv-python Pillow
```

| 套件 | 用途 |
|------|------|
| pymupdf | PDF 轉圖片 |
| pdfplumber | 提取文字座標 |
| easyocr | OCR 辨識 |
| opencv-python | 圖片處理 |
| Pillow | 圖片儲存 |

## 作業流程

### 1. 使用 pdfplumber 提取文字座標

```python
import pdfplumber

def extract_text_with_positions(pdf_path):
    all_texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            for word in words:
                all_texts.append({
                    'page': page_num,
                    'text': word['text'],
                    'x0': word['x0'],
                    'y0': word['top'],
                    'x1': word['x1'],
                    'y1': word['bottom'],
                })
    return all_texts
```

### 2. 偵測題號位置

題號格式通常為 `1.` `2.` ... `50.`

```python
import re

def find_question_starts(texts):
    questions = []
    for item in texts:
        text = item['text'].strip()
        match = re.match(r'^(\d{1,2})[.、．]$', text)
        if match:
            q_num = int(match.group(1))
            if 1 <= q_num <= 50:
                questions.append({
                    'num': q_num,
                    'page': item['page'],
                    'y0': item['y0'],
                    'y1': item['y1'],
                })
    return questions
```

### 3. PDF 轉圖片

使用 PyMuPDF 將每頁轉為 2x 解析度的 PNG：

```python
import fitz

def pdf_to_images(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    image_paths = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(2, 2)  # 2x 放大
        pix = page.get_pixmap(matrix=mat)
        img_path = f"{output_dir}/page_{page_num+1:03d}.png"
        pix.save(img_path)
        image_paths[page_num + 1] = img_path
    doc.close()
    return image_paths
```

### 4. 計算裁切邊界

每個題目從題號的 y 座標開始，到下一題號的 y 座標結束：

```python
def compute_question_bounds(questions_on_page, page_height):
    bounds = []
    questions_on_page.sort(key=lambda q: q['y0'])
    
    for i, q in enumerate(questions_on_page):
        y_start = q['y0'] - 10  # 留一點上方空間
        
        if i < len(questions_on_page) - 1:
            y_end = questions_on_page[i + 1]['y0']
        else:
            y_end = page_height
        
        bounds.append({
            'num': q['num'],
            'page': q['page'],
            'y_start': max(0, y_start),
            'y_end': min(page_height, y_end),
        })
    return bounds
```

### 5. 裁切圖片

注意：pdfplumber 使用 72 DPI 座標，圖片是 2x 放大，所以要乘以 2：

```python
import cv2
import numpy as np
from PIL import Image

def crop_image(image_path, y_start, y_end, output_path):
    data = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    
    y_start_px = int(y_start * 2)
    y_end_px = int(y_end * 2)
    
    cropped = img[y_start_px:y_end_px, :]
    cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
    Image.fromarray(cropped_rgb).save(output_path)
```

### 6. OCR 辨識

```python
import easyocr

reader = easyocr.Reader(['ch_tra', 'en'], gpu=True)

def ocr_image(image_path):
    data = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return reader.readtext(img, detail=1)
```

## 注意事項

### 中文路徑問題

OpenCV 的 `cv2.imread` 無法處理含中文的路徑。解決方案：

```python
# 讀取
data = np.fromfile(path, dtype=np.uint8)
img = cv2.imdecode(data, cv2.IMREAD_COLOR)

# 儲存 (使用 PIL)
from PIL import Image
Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(output_path)
```

### 題號偵測過濾

需要排除：
- 頁碼（格式：`第 X 頁`）
- 選項（格式：`(A)` `(B)` `(C)` `(D)`）
- 超出範圍的數字

### 跨頁面處理

同一題號可能出現在不同頁面（如頁碼），需要追蹤已處理的題號避免重複。

## 輸出結構

```
提取結果/
├── pages/              # 原始頁面圖片
├── q01.png ~ q50.png   # 每題裁切圖片
├── q01.md ~ q50.md     # 每題 OCR Markdown
└── summary.md          # 題目列表摘要
```

## 完整腳本位置

- 工作腳本：`C:\Users\4pins\AppData\Local\Temp\opencode\crop_ocr_v3.py`
- 輸出範例：`E:\01-Project\2026-08-Taipower-test\test-pdf\114-2025\電機\提取結果_v4\`
