"""
PDF 단어 추출 진단 스크립트
사용법: python scripts/debug_pdf.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import fitz

PDF_PATH = r'C:\Users\rkgml\Downloads\경제학_선택기출_20260521_194136\2021_국가직 7급(2차)_65446268_경제학-가.pdf'

doc = fitz.open(PDF_PATH)

for page_idx in range(min(3, len(doc))):
    page = doc[page_idx]
    pw = page.rect.width
    print(f'\n=== 페이지 {page_idx+1} (너비={pw:.0f}pt) ===')
    words = page.get_text('words')
    for w in words[:80]:  # 앞 80개 단어만
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
        print(f'  x={x0:6.1f} y={y0:6.1f}  "{text}"')

doc.close()
