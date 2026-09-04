#!/usr/bin/env python3
"""
台電歷屆考題下載腳本
下載114年度~103年度的共同科目和電機類別考題及解答
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

YEAR_ATTRIBUTES = {
    114: 4300, 113: 4298, 112: 4296, 111: 4224, 110: 4119,
    109: 3032, 108: 2714, 107: 2656, 106: 353, 105: 354,
    104: 355, 103: 559,
}

BASE_URL = "https://www.taipower.com.tw/2289/2544/2554/2556/"
DOWNLOAD_DIR = "/Users/4pins/Downloads/2026-06-01-pdf"
TARGET_CATEGORIES = ["共同科目", "電機"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}


def extract_descriptive_name(title_text):
    """Extract descriptive filename from link title attribute"""
    # Remove Chinese parentheses and trailing text
    title = re.sub(r'（.*?）', '', title_text)
    title = title.strip()
    # Add .pdf extension
    if not title.endswith('.pdf'):
        title += '.pdf'
    return title


def parse_page_for_pdfs(html_content, year):
    """Parse HTML page and extract PDF information by section"""
    soup = BeautifulSoup(html_content, "html.parser")
    pdfs = []

    # Find all li elements with p.title
    for li in soup.find_all('li'):
        title_p = li.find('p', class_='title')
        if not title_p:
            continue

        title_text = title_p.get_text(strip=True)

        # Check if this section matches target categories
        is_target = False
        category = None
        for cat in TARGET_CATEGORIES:
            if cat in title_text:
                is_target = True
                category = cat
                break

        if not is_target:
            continue

        # Find all PDF links in this section
        for link in li.find_all('a', href=True):
            href = link.get('href', '')
            href_clean = href.split('?')[0] if '?' in href else href

            if not href_clean.endswith('.pdf'):
                continue

            full_url = urljoin('https://www.taipower.com.tw', href)

            # Get descriptive name from link title, fallback to filename
            link_title = link.get('title', '')
            if link_title:
                filename = extract_descriptive_name(link_title)
            else:
                filename = href_clean.split('/')[-1]

            pdfs.append({
                'url': full_url,
                'filename': filename,
                'category': category,
                'year': year,
                'section_title': title_text
            })

    return pdfs


def download_pdf(url, filepath, session):
    """Download a PDF file"""
    try:
        response = session.get(url, headers=HEADERS, timeout=60, stream=True)
        response.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"  Error downloading {url}: {e}")
        return False


def main():
    """Main download function"""
    print("=" * 60)
    print("台電歷屆考題下載器")
    print("下載114年度~103年度的共同科目和電機類別考題及解答")
    print("=" * 60)

    session = requests.Session()
    total_downloaded = 0
    total_failed = 0

    for year in range(114, 102, -1):
        if year not in YEAR_ATTRIBUTES:
            print(f"\n年度 {year} 沒有對應的 q_attribute，跳過")
            continue

        q_attr = YEAR_ATTRIBUTES[year]
        print(f"\n{'='*50}")
        print(f"處理 {year}年度...")
        print(f"{'='*50}")

        year_dir = os.path.join(DOWNLOAD_DIR, f"{year}年度")
        os.makedirs(year_dir, exist_ok=True)

        url = f"{BASE_URL}?Page=1&PageSize=60&q_attribute={q_attr}"
        print(f"  Fetching: {url}")

        try:
            response = session.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            response.encoding = "utf-8"
        except Exception as e:
            print(f"  Error fetching page: {e}")
            continue

        pdfs = parse_page_for_pdfs(response.text, year)

        if not pdfs:
            print(f"  未找到符合條件的PDF")
            continue

        print(f"  找到 {len(pdfs)} 個PDF")

        for pdf_info in pdfs:
            category = pdf_info["category"]
            filename = pdf_info["filename"]
            section = pdf_info["section_title"]

            # Create category directory (include subcategory if exists)
            # e.g., "電機" or "電機(一)" or "電機(二)"
            subcategory = ""
            if "(" in section or "（" in section:
                # Extract subcategory like (一), (二)
                match = re.search(r'[（(]([^)）]+)[）)]', section)
                if match:
                    subcategory = match.group(0)

            if subcategory:
                category_dir = os.path.join(year_dir, f"{category}{subcategory}")
            else:
                category_dir = os.path.join(year_dir, category)
            os.makedirs(category_dir, exist_ok=True)

            filepath = os.path.join(category_dir, filename)

            if os.path.exists(filepath):
                print(f"  [SKIP] {filename} (已存在)")
                continue

            print(f"  [DOWNLOAD] {filename}...")
            print(f"           Section: {section}")

            if download_pdf(pdf_info["url"], filepath, session):
                print(f"  [OK] {filename}")
                total_downloaded += 1
            else:
                print(f"  [FAIL] {filename}")
                total_failed += 1

            time.sleep(0.5)

    print("\n" + "=" * 60)
    print("下載完成!")
    print(f"成功下載: {total_downloaded} 個檔案")
    print(f"下載失敗: {total_failed} 個檔案")
    print("=" * 60)


if __name__ == "__main__":
    main()
