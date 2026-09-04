import fitz
import re
import os
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

EXAM_PDF = r"E:\01-Project\2026-08-Taipower-test\test-pdf\105-2016\電機(甲)\105年新進職員甄試試題科目A_16.電機(甲)_電路學、電子學.pdf"
ANSWER_PDF = r"E:\01-Project\2026-08-Taipower-test\test-pdf\105-2016\電機(甲)\105年新進職員甄試解答科目A_16.電機(甲)_電路學、電子學.pdf"
OUTPUT_DIR = r"E:\01-Project\2026-08-Taipower-test\test-pdf\105-2016\電機(甲)\提取結果"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "完整解答.md")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Step 1: Extract answers from answer PDF ---
print("=== Extracting answers from answer PDF ===")
ans_doc = fitz.open(ANSWER_PDF)
full_ans_text = ""
for page in ans_doc:
    full_ans_text += page.get_text() + "\n"
ans_doc.close()

# Extract answers using the specified regex pattern
answer_pattern = r'\[\s*([A-E])\s*\]\s*\n?\s*(\d+)[\.\s]'
raw_matches = re.findall(answer_pattern, full_ans_text)
answers = {}
for letter, qnum in raw_matches:
    q = int(qnum)
    if 1 <= q <= 50:
        answers[q] = letter

print(f"Found {len(answers)} answers (Q1-Q50):")
for q in sorted(answers.keys())[:10]:
    print(f"  Q{q}: {answers[q]}")
print(f"  ... (showing first 10)")

# --- Step 2: Extract questions from exam PDF ---
print("\n=== Extracting questions from exam PDF ===")
exam_doc = fitz.open(EXAM_PDF)
full_exam_text = ""
for page in exam_doc:
    full_exam_text += page.get_text() + "\n"
exam_doc.close()

print(f"Exam text length: {len(full_exam_text)} characters")
print(f"First 500 chars:\n{full_exam_text[:500]}")

# Try to split by question numbers
# Common patterns: "1.", "1、", "（1）" etc.
# Let's try splitting by lines starting with a number
lines = full_exam_text.split('\n')
print(f"\nTotal lines: {len(lines)}")
for i, line in enumerate(lines[:30]):
    if line.strip():
        print(f"  Line {i}: {line.strip()[:80]}")

# Save full text for inspection
with open(os.path.join(OUTPUT_DIR, "exam_text.txt"), 'w', encoding='utf-8') as f:
    f.write(full_exam_text)

with open(os.path.join(OUTPUT_DIR, "answer_text.txt"), 'w', encoding='utf-8') as f:
    f.write(full_ans_text)

print(f"\nText files saved to {OUTPUT_DIR}")
print(f"Answers extracted: {len(answers)}")
