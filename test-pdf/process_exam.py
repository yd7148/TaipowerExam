"""
國營事業招考試題 PDF 批次處理腳本
功能：擷取文字、渲染圖片、提取答案
用法：python process_exam.py <年度資料夾> <科目資料夾> [解答PDF路徑]
"""
import sys, os, io, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pymupdf

def extract_text_from_pdf(pdf_path):
    """從PDF擷取全部文字"""
    doc = fitz.open(pdf_path)
    all_text = []
    for i, page in enumerate(doc):
        text = page.get_text()
        all_text.append(f"=== 第{i+1}頁 ===\n{text}")
    doc.close()
    return "\n".join(all_text)

def render_pages(pdf_path, output_dir, prefix="page", zoom=3):
    """將PDF每頁渲染為PNG"""
    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(zoom, zoom)
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for i, page in enumerate(doc):
        pix = page.get_text("rawdict")  # dummy
        pix = page.get_pixmap(matrix=mat)
        out_path = os.path.join(output_dir, f"{prefix}_{i+1:02d}.png")
        pix.save(out_path)
        paths.append(out_path)
    doc.close()
    return paths

def extract_answers_from_pdf(pdf_path):
    """從解答PDF提取答案（格式：[X] 或 X）"""
    doc = fitz.open(pdf_path)
    answers = {}
    for page in doc:
        text = page.get_text()
        # 匹配 [1]A, [1] A, 1.A, 1. A 等格式
        for m in re.finditer(r'\[?\s*(\d+)\s*\]?\s*[:.\-]?\s*([A-E])', text):
            q_num = int(m.group(1))
            ans = m.group(2)
            answers[q_num] = ans
    doc.close()
    return answers

def list_pdfs_in_dir(year_dir):
    """列出年度目錄下所有PDF"""
    pdfs = []
    for root, dirs, files in os.walk(year_dir):
        for f in sorted(files):
            if f.lower().endswith('.pdf'):
                pdfs.append(os.path.join(root, f))
    return pdfs

def main():
    base = r'E:\01-Project\2026-08-Taipower-test\test-pdf'
    
    if len(sys.argv) < 3:
        print("用法: python process_exam.py <年度> <科目>")
        print("例如: python process_exam.py 114-2025 電機")
        print("\n可用的年度科目:")
        for year_dir in sorted(os.listdir(base)):
            year_path = os.path.join(base, year_dir)
            if not os.path.isdir(year_path) or not year_dir[0:3].isdigit():
                continue
            for subject_dir in sorted(os.listdir(year_path)):
                subject_path = os.path.join(year_path, subject_dir)
                if os.path.isdir(subject_path):
                    pdfs = [f for f in os.listdir(subject_path) if f.lower().endswith('.pdf')]
                    print(f"  {year_dir}/{subject_dir} ({len(pdfs)} PDFs)")
        return
    
    year = sys.argv[1]
    subject = sys.argv[2]
    subject_path = os.path.join(base, year, subject)
    
    if not os.path.exists(subject_path):
        print(f"找不到: {subject_path}")
        return
    
    # 找試題和解答PDF
    exam_pdf = None
    answer_pdf = None
    for f in os.listdir(subject_path):
        if '解答' in f and f.lower().endswith('.pdf'):
            answer_pdf = os.path.join(subject_path, f)
        elif '試題' in f and f.lower().endswith('.pdf'):
            exam_pdf = os.path.join(subject_path, f)
    
    if not exam_pdf:
        # 也可能沒有明確標示，取所有PDF
        pdfs = [os.path.join(subject_path, f) for f in os.listdir(subject_path) if f.lower().endswith('.pdf')]
        if pdfs:
            exam_pdf = pdfs[0]
    
    print(f"\n年度: {year}")
    print(f"科目: {subject}")
    print(f"試題PDF: {exam_pdf}")
    print(f"解答PDF: {answer_pdf}")
    
    # 建立輸出目錄
    output_dir = os.path.join(subject_path, "提取結果")
    os.makedirs(output_dir, exist_ok=True)
    
    # 擷取試題文字
    if exam_pdf:
        print(f"\n--- 擷取試題文字 ---")
        text = extract_text_from_pdf(exam_pdf)
        text_path = os.path.join(output_dir, "試題全文.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"已儲存: {text_path}")
        
        # 渲染試題圖片
        print(f"渲染試題圖片...")
        img_paths = render_pages(exam_pdf, output_dir, prefix="試題")
        print(f"已渲染 {len(img_paths)} 頁")
    
    # 擷取解答
    if answer_pdf:
        print(f"\n--- 擷取解答 ---")
        text = extract_text_from_pdf(answer_pdf)
        text_path = os.path.join(output_dir, "解答全文.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"已儲存: {text_path}")
        
        answers = extract_answers_from_pdf(answer_pdf)
        print(f"找到 {len(answers)} 題答案:")
        for q in sorted(answers.keys()):
            print(f"  第{q}題: {answers[q]}")
        
        # 儲存答案JSON
        ans_path = os.path.join(output_dir, "answers.json")
        with open(ans_path, 'w', encoding='utf-8') as f:
            json.dump(answers, f, ensure_ascii=False, indent=2)
        print(f"已儲存: {ans_path}")
        
        # 渲染解答圖片
        print(f"渲染解答圖片...")
        img_paths = render_pages(answer_pdf, output_dir, prefix="解答")
        print(f"已渲染 {len(img_paths)} 頁")

if __name__ == "__main__":
    import fitz  # pymupdf
    main()
