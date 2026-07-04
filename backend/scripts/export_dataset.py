"""
파인튜닝용 데이터셋 추출 스크립트.

사용법:
    cd project_04/backend
    python scripts/export_dataset.py

출력:
    scripts/dataset.json  — 문제-풀이 쌍 (Alpaca 형식)
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from database import get_conn, _cursor

INSTRUCTION = "다음 경제학 기출문제를 풀어주세요. 정답과 각 선지별 해설을 작성하세요."

def main():
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute("""
        SELECT question_text, solution
        FROM problems
        WHERE question_text IS NOT NULL AND question_text != ''
          AND solution IS NOT NULL AND solution != ''
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    dataset = []
    for row in rows:
        dataset.append({
            "instruction": INSTRUCTION,
            "input": row["question_text"].strip(),
            "output": row["solution"].strip(),
        })
    skipped = 0

    out_path = os.path.join(os.path.dirname(__file__), 'dataset.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"완료: {len(dataset)}개 추출 / {skipped}개 스킵 (문제 텍스트 또는 풀이 없음)")
    print(f"저장 위치: {out_path}")

if __name__ == '__main__':
    main()
