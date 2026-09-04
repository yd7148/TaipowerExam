"""
台電招考試題批次處理腳本
功能：從PDF提取題目文字+答案，輸出JSON供後續解題
用法：python extract_exam.py <年度> <科目資料夾名>
"""
import sys, io, re, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import fitz  # pymupdf

def extract_answers_from_pdf(pdf_path):
    """從解答PDF提取答案 [X] 格式"""
    doc = fitz.open(pdf_path)
    answers = {}
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    
    # Pattern: [X] followed by question number
    for m in re.finditer(r'\[\s*([A-E])\s*\]\s*\n?\s*(\d+)[\.\s]', full_text):
        ans = m.group(1)
        q_num = int(m.group(2))
        if 1 <= q_num <= 50:
            answers[str(q_num)] = ans
    return answers, full_text

def extract_questions_from_pdf(pdf_path):
    """從試題PDF提取題目文字"""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text

def parse_questions(text):
    """解析題目文字為結構化資料"""
    questions = {}
    # Split by question numbers like "1." "2." etc.
    # Pattern: number followed by period and text
    parts = re.split(r'\n\s*(\d{1,2})[\.\s]', text)
    
    i = 0
    while i < len(parts) - 1:
        try:
            q_num = int(parts[i])
            if 1 <= q_num <= 50:
                q_text = parts[i + 1].strip()
                # Clean up: remove page headers, options formatting
                q_text = re.sub(r'\d+\s*\.\s*(電路學|電子學).*?第\s*\d+\s*頁.*?\n', '', q_text)
                q_text = re.sub(r'經濟部.*?甄試試題.*?\n', '', q_text)
                q_text = re.sub(r'類別:.*?\n', '', q_text)
                q_text = re.sub(r'科目:.*?\n', '', q_text)
                q_text = re.sub(r'注\s*\n\s*意\s*\n\s*事\s*\n?\s*項.*?(?=\d+\.)', '', q_text, flags=re.DOTALL)
                q_text = q_text.strip()
                if q_text:
                    questions[str(q_num)] = q_text
        except ValueError:
            pass
        i += 2
    return questions

def main():
    base = r'E:\01-Project\2026-08-Taipower-test\test-pdf'
    
    if len(sys.argv) < 3:
        print("用法: python extract_exam.py <年度> <科目資料夾>")
        print("例如: python extract_exam.py 113-2024 電機")
        return
    
    year = sys.argv[1]
    subject = sys.argv[2]
    subject_path = os.path.join(base, year, subject)
    
    if not os.path.exists(subject_path):
        print(f"找不到: {subject_path}")
        return
    
    # Find exam and answer PDFs for 科目A (電路學電子學)
    exam_pdf = None
    answer_pdf = None
    for f in os.listdir(subject_path):
        if not f.endswith('.pdf'):
            continue
        if '解答' in f and ('電路學' in f or '科目A' in f):
            answer_pdf = os.path.join(subject_path, f)
        elif '試題' in f and ('電路學' in f or '科目A' in f):
            exam_pdf = os.path.join(subject_path, f)
    
    if not exam_pdf:
        print(f"找不到科目A試題PDF")
        return
    
    print(f"試題: {os.path.basename(exam_pdf)}")
    print(f"解答: {os.path.basename(answer_pdf) if answer_pdf else '無'}")
    
    # Extract
    exam_text = extract_questions_from_pdf(exam_pdf)
    questions = parse_questions(exam_text)
    
    answers = {}
    if answer_pdf:
        answers, ans_text = extract_answers_from_pdf(answer_pdf)
    
    # Output
    output = {
        "year": year,
        "subject": subject,
        "exam_file": os.path.basename(exam_pdf),
        "answer_file": os.path.basename(answer_pdf) if answer_pdf else None,
        "answers": answers,
        "questions": questions,
        "exam_text_full": exam_text[:5000]  # First 5000 chars for reference
    }
    
    # Save
    out_dir = os.path.join(subject_path, "提取結果")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "exam_data.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n已提取 {len(questions)} 題, {len(answers)} 個答案")
    print(f"輸出: {out_path}")
    
    # Print summary
    print(f"\n答案一覽:")
    for q in sorted(answers.keys(), key=int):
        print(f"  Q{q}: {answers[q]}")
    
    missing = sorted(set(range(1,51)) - set(int(k) for k in answers.keys()))
    if missing:
        print(f"  缺少: {missing}")

if __name__ == "__main__":
    main()
