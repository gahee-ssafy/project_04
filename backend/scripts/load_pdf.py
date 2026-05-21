"""
PDF 기출문제 -> 25문제 이미지 크롭 -> DB 저장
사용법: python scripts/load_pdf.py
"""
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import fitz
from database import get_conn

DPI = 150
SCALE = DPI / 72.0

TOPIC_MAP = {
    '수요': '미시경제학', '공급': '미시경제학', '탄력성': '미시경제학',
    '효용': '미시경제학', '소비': '미시경제학', '생산': '미시경제학',
    '비용': '미시경제학', '독점': '미시경제학', '과점': '미시경제학',
    '외부성': '미시경제학', '공공재': '미시경제학', '정보': '미시경제학',
    '게임': '미시경제학', '노동': '미시경제학', '소득분배': '미시경제학',
    '지니': '미시경제학',
    'GDP': '거시경제학', '국민소득': '거시경제학', '인플레이션': '거시경제학',
    '통화': '거시경제학', '금리': '거시경제학', '이자율': '거시경제학',
    '재정': '거시경제학', '총수요': '거시경제학', '총공급': '거시경제학',
    '필립스': '거시경제학', '솔로우': '거시경제학', '성장': '거시경제학',
    'IS-LM': '거시경제학', '승수': '거시경제학',
    '환율': '국제경제학', '무역': '국제경제학', '관세': '국제경제학',
    '수출': '국제경제학', '경상수지': '국제경제학', '헥셔': '국제경제학',
}

def guess_topic(text):
    for kw, topic in TOPIC_MAP.items():
        if kw in text:
            return topic
    return '경제학'

def guess_difficulty(q_num):
    if q_num <= 8: return 2
    elif q_num <= 16: return 3
    else: return 4

# ── 문제 번호 위치 탐색 ────────────────────────────────────
def _find_question_pos(page, q_num):
    """단어 단위로 'N.' 을 찾아 (x0, y0) 반환. 2열 레이아웃 양쪽 대응."""
    words = page.get_text('words')
    target = f'{q_num}.'
    pw = page.rect.width
    col_threshold = pw * 0.45

    for w in words:
        if w[4].strip() == target:
            x0 = w[0]
            in_left  = x0 <= pw * 0.15
            in_right = col_threshold < x0 <= pw * 0.65
            if in_left or in_right:
                return x0, w[1]
    return None

# ── 문제 이미지 크롭 ──────────────────────────────────────
def crop_question_image(doc, page_idx, q_num, next_q_num):
    """같은 열 내 다음 문제 y좌표로 하단 경계 결정. raw PNG bytes 반환."""
    page = doc[page_idx]
    pos = _find_question_pos(page, q_num)
    if pos is None:
        return None, ''

    x0, top = pos
    pw = page.rect.width
    col_mid = pw / 2

    col_x0, col_x1 = (0, col_mid) if x0 < col_mid else (col_mid, pw)

    bottom = None
    if next_q_num is not None:
        next_pos = _find_question_pos(page, next_q_num)
        if next_pos:
            same_col = (x0 < col_mid) == (next_pos[0] < col_mid)
            if same_col and next_pos[1] > top:
                bottom = next_pos[1]

    bottom = bottom if bottom else page.rect.height - 30
    clip = fitz.Rect(col_x0, max(0, top - 4), col_x1, bottom - 4)

    if clip.width <= 0 or clip.height <= 0:
        return None, ''

    pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=clip)
    text = page.get_text(clip=clip)
    return pix.tobytes('png'), text.strip()

# ── 문제별 페이지 매핑 ────────────────────────────────────
def find_q_pages(doc):
    """q_num -> page_idx 딕셔너리. 첫 발견 페이지 기준."""
    q_to_page = {}
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        for q_num in range(1, 26):
            if q_num not in q_to_page and _find_question_pos(page, q_num) is not None:
                q_to_page[q_num] = page_idx
    return q_to_page

# ── DB 저장 ───────────────────────────────────────────────
def load_pdf(pdf_path, exam_year, exam_round):
    print(f'[로드] {os.path.basename(pdf_path)}  ({exam_year}년 {exam_round}회차)')

    doc = fitz.open(pdf_path)
    q_to_page = find_q_pages(doc)
    detected = sorted(q_to_page.keys())
    print(f'  감지된 문제 번호: {detected}')

    missing = [n for n in range(1, 26) if n not in q_to_page]
    if missing:
        print(f'  [주의] 감지 안 된 번호: {missing}')

    db = get_conn()
    deleted = db.execute(
        'DELETE FROM problems WHERE exam_year=? AND exam_round=?',
        (exam_year, exam_round)
    ).rowcount
    if deleted:
        print(f'  기존 {deleted}개 삭제')
    db.commit()

    count = 0
    for q_num in range(1, 26):
        page_idx = q_to_page.get(q_num)
        if page_idx is None:
            continue

        # 같은 페이지 내 다음 문제 번호
        same_page_qs = sorted(qn for qn, pi in q_to_page.items() if pi == page_idx)
        idx_in_page = same_page_qs.index(q_num)
        next_on_page = same_page_qs[idx_in_page + 1] if idx_in_page + 1 < len(same_page_qs) else None

        png_bytes, text = crop_question_image(doc, page_idx, q_num, next_on_page)

        topic = guess_topic(text)
        difficulty = guess_difficulty(q_num)
        label = f'{exam_year}년 {exam_round}회차 {q_num}번'

        db.execute(
            '''INSERT INTO problems
               (question, topic, difficulty, exam_year, exam_round,
                image_data, image_mime, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))''',
            (label, topic, difficulty, exam_year, exam_round,
             png_bytes, 'image/png' if png_bytes else None)
        )
        count += 1
        status = 'img OK' if png_bytes else 'img FAIL'
        print(f'  [{status}] {q_num:2d}번 [{topic}]  {text[:40].replace(chr(10), " ")}')

    db.commit()
    doc.close()
    db.close()
    print(f'  -> {count}개 저장 완료\n')
    return count

# ── 엔트리포인트 ──────────────────────────────────────────
PDF_DIR = r'C:\Users\rkgml\Downloads\경제학_선택기출_20260521_194136'

ALL_PDFS = [
    ('2021_국가직 7급(2차)_65446268_경제학-가.pdf', 2021, 1),
#     ('2022_국가직 7급(2차)_92874392_221015 국가 7급 2차 경제학-나.pdf', 2022, 1),
#     ('2023_국가직 7급(2차)_112625956_230923 국가 7급 2차 경제학-가.pdf', 2023, 1),
#     ('2024_국가직 7급(2차)_130883624_241012 국가 7급 2차 경제학-나.pdf', 2024, 1),
#     ('2025_국가직 7급(2차)_130912469_250920 국가 7급 2차 경제학-가.pdf', 2025, 1),
]

if __name__ == '__main__':
    total = 0
    for filename, year, round_ in ALL_PDFS:
        path = os.path.join(PDF_DIR, filename)
        if not os.path.exists(path):
            print(f'[건너뜀] 파일 없음: {filename}')
            continue
        total += load_pdf(path, year, round_)
    print(f'=== 전체 {total}개 문제 저장 완료 ===')
