"""problems 테이블의 모든 문제에 concept 태그를 일괄 저장.

개념 추출 우선순위:
  1. question_text (이미지 문제에서 추출한 실제 질문 텍스트)  ← 가장 정확
  2. question (문제 제목/레이블)
  3. solution (풀이 — 관련 없는 개념이 많이 포함될 수 있으므로 마지막)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import get_conn, init_db
from services.report import extract_concept

def run():
    init_db()  # concept, question_text 컬럼 마이그레이션 포함
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, question, question_text, solution FROM problems"
    ).fetchall()

    tagged, skipped = 0, 0
    for row in rows:
        pid       = row["id"]
        question  = row["question"] or ""
        q_text    = row["question_text"] or ""
        solution  = row["solution"] or ""

        # question_text가 있으면 그것만 사용 (풀이 오염 방지)
        # 없으면 question + solution 조합 (기존 방식)
        if q_text.strip():
            text = q_text
        else:
            text = f"{question} {solution}"

        concept = extract_concept(text)
        if concept:
            conn.execute(
                "UPDATE problems SET concept = ? WHERE id = ?",
                (concept, pid)
            )
            tagged += 1
            label = q_text[:40] if q_text else question
            print(f"  [{pid}] {label} → {concept}")
        else:
            skipped += 1
            label = q_text[:40] if q_text else question
            print(f"  [{pid}] {label} → (미매칭)")

    conn.commit()
    conn.close()
    print(f"\n완료: {tagged}개 태깅, {skipped}개 미매칭")

if __name__ == "__main__":
    run()
