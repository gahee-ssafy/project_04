"""problems 테이블의 모든 문제에 concept 태그를 일괄 저장."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import get_conn, init_db
from services.report import extract_concept

def run():
    init_db()  # concept 컬럼 마이그레이션 포함
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, question, solution FROM problems"
    ).fetchall()

    tagged, skipped = 0, 0
    for row in rows:
        pid, question, solution = row["id"], row["question"], row["solution"]
        text = f"{question or ''} {solution or ''}"
        concept = extract_concept(text)
        if concept:
            conn.execute(
                "UPDATE problems SET concept = ? WHERE id = ?",
                (concept, pid)
            )
            tagged += 1
            print(f"  [{pid}] {question} → {concept}")
        else:
            skipped += 1
            print(f"  [{pid}] {question} → (미매칭)")

    conn.commit()
    conn.close()
    print(f"\n완료: {tagged}개 태깅, {skipped}개 미매칭")

if __name__ == "__main__":
    run()
