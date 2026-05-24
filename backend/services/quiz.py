"""
OX 복습 퀴즈 서비스
- 오답노트 풀이(선지별 해설)를 파싱해 OX 문제 생성 (AI 미사용)
- 틀렸을 때 관련 기출문제 키워드 매칭
"""
import re
import base64
import random
from database import get_conn
from services.report import ECON_CONCEPTS

CHOICE_RE = re.compile(r'^([①②③④⑤])\s*(.*)')


# ─── 풀이 → OX 파싱 ─────────────────────────────────────────────
def _parse_choices(solution: str) -> list[dict]:
    """
    [풀이] 섹션에서 선지별 {marker, text, is_correct} 추출.
    '정답.' 이 포함된 선지 = O, 나머지 = X
    """
    if not solution:
        return []

    in_section = False
    items = []

    for raw in solution.split('\n'):
        line = raw.strip()
        if not line:
            continue
        if line.startswith('[풀이]'):
            in_section = True
            continue
        if line.startswith('[') and in_section:
            break
        if not in_section:
            continue

        m = CHOICE_RE.match(line)
        if m:
            marker = m.group(1)
            text   = m.group(2).strip()
            is_correct = '정답.' in text
            text_clean = text.replace('정답.', '').strip()
            if text_clean:
                items.append({
                    "marker":     marker,
                    "text":       text_clean,
                    "is_correct": is_correct,
                })
        elif items:
            # 선지 이어지는 줄
            items[-1]["text"] += ' ' + line

    return items


# ─── 관련 기출문제 매칭 ──────────────────────────────────────────
def _find_related_problem(ox_text: str) -> dict | None:
    """OX 문제 텍스트에서 개념 추출 → 기출문제 키워드 매칭."""
    # 1. 개념 추출
    best_concept, best_score = None, 0
    for concept, keywords in ECON_CONCEPTS.items():
        score = sum(ox_text.count(kw) for kw in keywords)
        if score > best_score:
            best_score = score
            best_concept = concept

    if not best_concept or best_score == 0:
        # 개념 없으면 전체 단어 빈도로 fallback
        keywords_fallback = [w for w in ox_text.split() if len(w) >= 2]
    else:
        keywords_fallback = ECON_CONCEPTS[best_concept]

    conn = get_conn()
    rows = conn.execute(
        """SELECT id, question, solution, image_data, image_mime,
                  exam_year, exam_round, correct_answer
           FROM problems
           WHERE solution IS NOT NULL AND solution != ''""",
    ).fetchall()
    conn.close()

    best_problem, best_match = None, 0
    for row in rows:
        sol = row['solution'] or ''
        score = sum(sol.count(kw) for kw in keywords_fallback)
        if score > best_match:
            best_match = score
            best_problem = row

    if not best_problem or best_match == 0:
        return None

    result = dict(best_problem)
    if result.get('image_data'):
        result['image_data'] = base64.b64encode(result['image_data']).decode('utf-8')
    return result


# ─── 퀴즈 생성 ───────────────────────────────────────────────────
def generate_quiz(user_id: int) -> list[dict]:
    """
    오답노트 풀이에서 OX 퀴즈 생성.
    반환: [{ id, source_label, marker, text, is_correct }, ...]
    """
    conn = get_conn()
    rows = conn.execute(
        """SELECT s.id, s.question, s.answer
           FROM sessions s
           WHERE s.user_id = ?
             AND (s.question LIKE '[오답노트]%' OR s.question LIKE '[모의고사]%')
             AND s.answer IS NOT NULL AND s.answer != ''
           ORDER BY s.created_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()

    items = []
    for row in rows:
        choices = _parse_choices(row['answer'])
        label   = re.sub(r'^\[(오답노트|모의고사)\]\s*', '', row['question'])
        for c in choices:
            items.append({
                "id":           f"{row['id']}_{c['marker']}",
                "session_id":   row['id'],
                "source_label": label[:30] + ('…' if len(label) > 30 else ''),
                "marker":       c['marker'],
                "text":         c['text'],
                "is_correct":   c['is_correct'],
            })

    random.shuffle(items)
    return items[:15]   # 최대 15문제


def get_related_problem(ox_text: str) -> dict | None:
    return _find_related_problem(ox_text)
