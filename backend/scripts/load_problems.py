"""
PDF 기출문제를 문제별 이미지로 크롭해서 DB에 저장
사용법: python scripts/load_problems.py
"""
import re
import sys
import os
import base64
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import fitz  # pymupdf
from database import get_conn

PDF_FILES = [
    (r'C:\Users\rkgml\Downloads\경제학_선택기출_20260521_194136\2021_국가직 7급(2차)_65446268_경제학-가.pdf', 2021, 1),
    (r'C:\Users\rkgml\Downloads\경제학_선택기출_20260521_194136\2022_국가직 7급(2차)_92874392_221015 국가 7급 2차 경제학-나.pdf', 2022, 1),
    (r'C:\Users\rkgml\Downloads\경제학_선택기출_20260521_194136\2023_국가직 7급(2차)_112625956_230923 국가 7급 2차 경제학-가.pdf', 2023, 1),
    (r'C:\Users\rkgml\Downloads\경제학_선택기출_20260521_194136\2024_국가직 7급(2차)_130883624_241012 국가 7급 2차 경제학-나.pdf', 2024, 1),
    (r'C:\Users\rkgml\Downloads\경제학_선택기출_20260521_194136\2025_국가직 7급(2차)_130912469_250920 국가 7급 2차 경제학-가.pdf', 2025, 1),
]

TOPIC_KEYWORDS = {
    '수요': '미시경제학', '공급': '미시경제학', '탄력성': '미시경제학',
    '효용': '미시경제학', '소비': '미시경제학', '생산': '미시경제학',
    '비용': '미시경제학', '독점': '미시경제학', '과점': '미시경제학',
    '외부성': '미시경제학', '공공재': '미시경제학', '정보': '미시경제학',
    '게임': '미시경제학', '노동': '미시경제학',
    'GDP': '거시경제학', '국민소득': '거시경제학', '인플레이션': '거시경제학',
    '통화': '거시경제학', '금리': '거시경제학', '이자율': '거시경제학',
    '재정': '거시경제학', '총수요': '거시경제학', '총공급': '거시경제학',
    '필립스': '거시경제학', '솔로우': '거시경제학', '성장': '거시경제학',
    '환율': '국제경제학', '무역': '국제경제학', '관세': '국제경제학',
    '수출': '국제경제학', '수입': '국제경제학', '경상수지': '국제경제학',
}

def guess_topic(text):
    for kw, topic in TOPIC_KEYWORDS.items():
        if kw in text:
            return topic
    return '경제학'

def guess_difficulty(q_num):
    if q_num <= 8: return 2
    elif q_num <= 16: return 3
    else: return 4

# ── 문제 시작 블록 찾기 ─────────────────────────────────
# "1.", "문 1.", "문  1." 등 다양한 패턴 처리
Q_START_PATTERN = re.compile(r'^(?:문\s*)?\s*(\d{1,2})\.\s')

def is_question_start(text):
    """텍스트 블록이 문제 번호로 시작하는지 확인. 번호 반환 or None"""
    m = Q_START_PATTERN.match(text.strip())
    if m:
        num = int(m.group(1))
        if 1 <= num <= 25:
            return num
    return None

# ── 페이지별 문제 시작 위치(y좌표) 수집 ─────────────────
def find_question_positions(doc):
    """
    반환: list of (page_idx, y_top, q_num)
    페이지 헤더(상단 ~85px)는 무시
    """
    positions = []
    for page_idx, page in enumerate(doc):
        blocks = page.get_text('blocks')
        for b in blocks:
            x0, y0, x1, y1, text, bno, btype = b
            if btype != 0:  # 텍스트 블록만
                continue
            if y0 < 85:     # 헤더 영역 스킵
                continue
            q_num = is_question_start(text)
            if q_num is not None:
                positions.append((page_idx, y0, q_num))

    # 번호순 정렬, 중복 제거(첫 번째만)
    positions.sort(key=lambda x: x[2])
    seen = set()
    unique = []
    for item in positions:
        if item[2] not in seen:
            seen.add(item[2])
            unique.append(item)
    return unique

# ── 문제 영역 이미지 크롭 ────────────────────────────────
DPI = 150
SCALE = DPI / 72.0   # PDF 기본 72dpi → 150dpi
PADDING_BOTTOM = 8   # 다음 문제 시작 위에 약간 여백 제거

def crop_question_image(doc, positions, idx):
    """positions[idx] 문제의 이미지를 PNG bytes로 반환"""
    page_idx, y_top, q_num = positions[idx]
    page = doc[page_idx]
    page_height = page.rect.height

    # 이 문제의 끝 y좌표 결정
    if idx + 1 < len(positions):
        next_page_idx, next_y, _ = positions[idx + 1]
        if next_page_idx == page_idx:
            # 같은 페이지 → 다음 문제 시작 바로 위
            y_bottom = next_y - PADDING_BOTTOM
        else:
            # 다음 문제가 다른 페이지 → 현재 페이지 하단
            y_bottom = page_height - 30
    else:
        # 마지막 문제 → 현재 페이지 하단
        y_bottom = page_height - 30

    # 약간의 여백 추가 (위쪽)
    y_top = max(0, y_top - 4)

    # 전체 너비로 크롭
    rect = fitz.Rect(30, y_top, page.rect.width - 30, y_bottom)
    mat = fitz.Matrix(SCALE, SCALE)
    clip = rect
    pix = page.get_pixmap(matrix=mat, clip=clip)
    return pix.tobytes('png')

# ── 텍스트 추출 (주제/난이도 추정용) ─────────────────────
def extract_question_text(doc, positions, idx):
    page_idx, y_top, q_num = positions[idx]
    page = doc[page_idx]
    page_height = page.rect.height

    if idx + 1 < len(positions):
        next_page_idx, next_y, _ = positions[idx + 1]
        y_bottom = next_y if next_page_idx == page_idx else page_height
    else:
        y_bottom = page_height

    rect = fitz.Rect(0, y_top, page.rect.width, y_bottom)
    return page.get_text(clip=rect).strip()

# ── 메인 로딩 함수 ────────────────────────────────────────
def load_pdf_to_db(pdf_path, exam_year, exam_round):
    print(f'\n[파싱] {os.path.basename(pdf_path)} ({exam_year}년 {exam_round}회차)')

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f'  [오류] PDF 열기 실패: {e}')
        return 0

    positions = find_question_positions(doc)
    print(f'  발견된 문제 수: {len(positions)}개  ({[p[2] for p in positions]})')

    if len(positions) == 0:
        print('  [오류] 문제를 찾지 못했습니다.')
        doc.close()
        return 0

    db = get_conn()
    existing = db.execute(
        'SELECT COUNT(*) as cnt FROM problems WHERE exam_year=? AND exam_round=?',
        (exam_year, exam_round)
    ).fetchone()
    if existing['cnt'] > 0:
        print(f'  [경고] 기존 {existing["cnt"]}개 삭제 후 재삽입...')
        db.execute('DELETE FROM problems WHERE exam_year=? AND exam_round=?', (exam_year, exam_round))
        db.commit()

    count = 0
    for i, (page_idx, y_top, q_num) in enumerate(positions):
        try:
            png_bytes = crop_question_image(doc, positions, i)
            img_b64 = base64.b64encode(png_bytes).decode('utf-8')
        except Exception as e:
            print(f'  [오류] {q_num}번 이미지 크롭 실패: {e}')
            img_b64 = None

        question_text = extract_question_text(doc, positions, i)
        topic = guess_topic(question_text)
        difficulty = guess_difficulty(q_num)

        # question 필드에는 간단한 레이블만 (이미지가 본체)
        short_label = question_text[:80].replace('\n', ' ').strip()

        db.execute(
            '''INSERT INTO problems
               (question, topic, difficulty, exam_year, exam_round, image_data, image_mime, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))''',
            (short_label, topic, difficulty, exam_year, exam_round,
             img_b64, 'image/png' if img_b64 else None)
        )
        count += 1
        print(f'  [OK] {q_num:2d}번 [{topic}] p{page_idx+1} y={y_top:.0f}  {short_label[:35]}...')

    db.commit()
    doc.close()
    db.close()
    print(f'  -> {count}개 문제 저장 완료!')
    return count

def main():
    total = 0
    for pdf_path, year, round_ in PDF_FILES:
        if not os.path.exists(pdf_path):
            print(f'[오류] 파일 없음: {pdf_path}')
            continue
        count = load_pdf_to_db(pdf_path, year, round_)
        total += count
    print(f'\n전체 {total}개 문제 이미지 저장 완료!')

if __name__ == '__main__':
    main()
