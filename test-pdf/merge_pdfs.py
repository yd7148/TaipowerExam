#!/usr/bin/env python3
"""
合併台電歷屆考題PDF
依類別合併成單一檔案
"""

import os
import glob
from pypdf import PdfWriter

BASE_DIR = "/Users/4pins/Downloads/2026-06-01-pdf"

# 定義合併規則：(搜尋關鍵字, 輸出檔名)
MERGE_RULES = [
    # 1. 試題科目_共同科目
    {
        "name": "試題科目_共同科目",
        "output": "歷年試題科目_共同科目_合併.pdf",
        "match": lambda f: "共同科目" in f and "試題" in f and "解答" not in f,
    },
    # 2. 試題解答_共同科目
    {
        "name": "試題解答_共同科目",
        "output": "歷年試題解答_共同科目_合併.pdf",
        "match": lambda f: "共同科目" in f and "解答" in f,
    },
    # 3. 試題科目A_電機_電路學、電子學
    {
        "name": "試題科目A_電機_電路學電子學",
        "output": "歷年試題科目A_電機_電路學電子學_合併.pdf",
        "match": lambda f: "電機" in f and "科目A" in f and "電路學" in f and "試題" in f and "解答" not in f,
    },
    # 4. 試題解答A_電機_電路學、電子學
    {
        "name": "試題解答A_電機_電路學電子學",
        "output": "歷年試題解答A_電機_電路學電子學_合併.pdf",
        "match": lambda f: "電機" in f and "科目A" in f and "電路學" in f and "解答" in f,
    },
    # 5. 試題科目B_電機_電力系統、電機機械
    {
        "name": "試題科目B_電機_電力系統電機機械",
        "output": "歷年試題科目B_電機_電力系統電機機械_合併.pdf",
        "match": lambda f: "電機" in f and "科目B" in f and "電力系統" in f and "試題" in f and "解答" not in f,
    },
]


def find_matching_files(base_dir, match_func):
    """Find all PDF files matching the criteria"""
    all_pdfs = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".pdf"):
                filepath = os.path.join(root, file)
                if match_func(filepath):
                    all_pdfs.append(filepath)
    
    # Sort by year (extract year from path)
    def get_year(path):
        import re
        match = re.search(r'(\d{3})年度', path)
        if match:
            return int(match.group(1))
        return 0
    
    all_pdfs.sort(key=get_year)
    return all_pdfs


def merge_pdfs(pdf_list, output_path):
    """Merge multiple PDFs into one"""
    writer = PdfWriter()
    
    for pdf_path in pdf_list:
        try:
            writer.append(pdf_path)
        except Exception as e:
            print(f"  Error reading {os.path.basename(pdf_path)}: {e}")
    
    with open(output_path, "wb") as f:
        writer.write(f)
    
    return len(writer.pages)


def main():
    print("=" * 60)
    print("台電歷屆考題PDF合併器")
    print("=" * 60)
    
    total_files = 0
    
    for rule in MERGE_RULES:
        print(f"\n{'='*50}")
        print(f"合併: {rule['name']}")
        print(f"{'='*50}")
        
        # Find matching files
        files = find_matching_files(BASE_DIR, rule["match"])
        
        if not files:
            print("  未找到符合條件的檔案")
            continue
        
        print(f"  找到 {len(files)} 個檔案:")
        for f in files:
            # Show relative path
            rel_path = os.path.relpath(f, BASE_DIR)
            print(f"    - {rel_path}")
        
        # Merge
        output_path = os.path.join(BASE_DIR, rule["output"])
        pages = merge_pdfs(files, output_path)
        
        file_size = os.path.getsize(output_path) / 1024 / 1024
        print(f"\n  輸出: {rule['output']}")
        print(f"  頁數: {pages} 頁")
        print(f"  大小: {file_size:.2f} MB")
        
        total_files += len(files)
    
    print("\n" + "=" * 60)
    print("合併完成!")
    print(f"共處理 {total_files} 個檔案，產生 {len(MERGE_RULES)} 個合併檔案")
    print("=" * 60)


if __name__ == "__main__":
    main()
