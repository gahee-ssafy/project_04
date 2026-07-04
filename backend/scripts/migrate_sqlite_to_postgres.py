"""
SQLite → PostgreSQL 데이터 마이그레이션 스크립트.

사용법:
    cd project_04/backend
    python scripts/migrate_sqlite_to_postgres.py

주의: PostgreSQL이 실행 중이어야 합니다 (docker compose up db).
"""
import sys
import os
import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
from database import init_db

SQLITE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "app.db",
)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/app",
)


def sqlite_rows(conn, sql, params=()):
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def migrate():
    print(f"SQLite: {SQLITE_PATH}")
    print(f"PostgreSQL: {DATABASE_URL}\n")

    if not os.path.exists(SQLITE_PATH):
        print(f"오류: SQLite 파일을 찾을 수 없습니다 — {SQLITE_PATH}")
        sys.exit(1)

    print("PostgreSQL 테이블 초기화 중...")
    init_db()
    print("테이블 초기화 완료\n")

    src = sqlite3.connect(SQLITE_PATH)
    dst = psycopg2.connect(DATABASE_URL)
    dst.autocommit = False
    cur = dst.cursor()

    # FK 제약 일시 비활성화 (삭제된 레코드를 참조하는 고아 데이터 허용)
    cur.execute("SET session_replication_role = replica")

    # 외래키 의존 순서대로 이전
    tables = [
        ("users", _migrate_users),
        ("problems", _migrate_problems),
        ("sessions", _migrate_sessions),
        ("user_summaries", _migrate_user_summaries),
        ("memos", _migrate_memos),
        ("exam_attempts", _migrate_exam_attempts),
        ("notebook_chats", _migrate_notebook_chats),
        ("learning_reports", _migrate_learning_reports),
        ("credit_logs", _migrate_credit_logs),
        ("quiz_attempts", _migrate_quiz_attempts),
    ]

    for table_name, fn in tables:
        print(f"  {table_name} 이전 중...", end=" ")
        count = fn(src, cur)
        print(f"{count}건 완료")

    # FK 제약 복원 및 데이터 커밋
    cur.execute("SET session_replication_role = DEFAULT")
    dst.commit()

    # SERIAL 시퀀스를 현재 max(id)에 맞게 재설정
    serial_tables = [
        "users", "problems", "sessions",
        "memos", "exam_attempts", "notebook_chats",
        "learning_reports", "quiz_attempts",
    ]
    print("\n시퀀스 재설정 중...")
    for t in serial_tables:
        cur.execute(f"SELECT MAX(id) FROM {t}")
        row = cur.fetchone()
        max_id = row[0] if row and row[0] else 0
        cur.execute(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), %s)", (max(max_id, 1),))
    dst.commit()
    src.close()
    cur.close()
    dst.close()
    print("\n마이그레이션 완료!")


# ──────────────────────────────────────────────
def _migrate_users(src, cur):
    rows = sqlite_rows(src, "SELECT * FROM users")
    for r in rows:
        cur.execute(
            """INSERT INTO users (id, username, password, credits, created_at)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            (r["id"], r["username"], r["password"],
             r.get("credits", 30), r.get("created_at")),
        )
    return len(rows)


def _migrate_problems(src, cur):
    rows = sqlite_rows(src, "SELECT * FROM problems")
    for r in rows:
        image = bytes(r["image_data"]) if r.get("image_data") else None
        cur.execute(
            """INSERT INTO problems
               (id, topic, question, difficulty, solution, correct_answer,
                concept, question_text, embedding, image_data, image_mime,
                exam_year, exam_round, exam_type, ncs_agency, ncs_domain, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (id) DO NOTHING""",
            (r["id"], r["topic"], r["question"], r["difficulty"],
             r.get("solution"), r.get("correct_answer"), r.get("concept"),
             r.get("question_text"), r.get("embedding"),
             psycopg2.Binary(image) if image else None,
             r.get("image_mime"), r.get("exam_year"), r.get("exam_round"),
             r.get("exam_type", "civil"), r.get("ncs_agency"), r.get("ncs_domain"),
             r.get("created_at")),
        )
    return len(rows)


def _migrate_sessions(src, cur):
    rows = sqlite_rows(src, "SELECT * FROM sessions")
    for r in rows:
        image = bytes(r["image_data"]) if r.get("image_data") else None
        cur.execute(
            """INSERT INTO sessions
               (id, user_id, question, answer, image_data, image_mime,
                embedding, problem_id, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (id) DO NOTHING""",
            (r["id"], r.get("user_id"), r["question"], r.get("answer"),
             psycopg2.Binary(image) if image else None,
             r.get("image_mime"), r.get("embedding"), r.get("problem_id"),
             r.get("created_at")),
        )
    return len(rows)


def _migrate_user_summaries(src, cur):
    rows = sqlite_rows(src, "SELECT * FROM user_summaries")
    for r in rows:
        cur.execute(
            """INSERT INTO user_summaries (id, user_id, summary, created_at)
               VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING""",
            (r["id"], r["user_id"], r["summary"], r.get("created_at")),
        )
    return len(rows)


def _migrate_memos(src, cur):
    rows = sqlite_rows(src, "SELECT * FROM memos")
    for r in rows:
        cur.execute(
            """INSERT INTO memos (id, user_id, session_id, memo, rating, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING""",
            (r["id"], r["user_id"], r["session_id"],
             r.get("memo", ""), r.get("rating", 3), r.get("updated_at")),
        )
    return len(rows)


def _migrate_exam_attempts(src, cur):
    rows = sqlite_rows(src, "SELECT * FROM exam_attempts")
    for r in rows:
        cur.execute(
            """INSERT INTO exam_attempts
               (id, user_id, exam_year, exam_round, problem_id, user_answer,
                is_correct, exam_type, ncs_agency, ncs_domain, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (id) DO NOTHING""",
            (r["id"], r["user_id"], r["exam_year"], r["exam_round"],
             r["problem_id"], r.get("user_answer"), r.get("is_correct", 0),
             r.get("exam_type", "civil"), r.get("ncs_agency"), r.get("ncs_domain"),
             r.get("created_at")),
        )
    return len(rows)


def _migrate_notebook_chats(src, cur):
    rows = sqlite_rows(src, "SELECT * FROM notebook_chats")
    for r in rows:
        cur.execute(
            """INSERT INTO notebook_chats
               (id, user_id, notebook_session_id, messages, updated_at)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING""",
            (r["id"], r["user_id"], r["notebook_session_id"],
             r.get("messages", "[]"), r.get("updated_at")),
        )
    return len(rows)


def _migrate_learning_reports(src, cur):
    rows = sqlite_rows(src, "SELECT * FROM learning_reports")
    for r in rows:
        cur.execute(
            """INSERT INTO learning_reports
               (id, user_id, ai_pattern, ai_weakness, ai_advice,
                weekly_message, weekly_at, generated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING""",
            (r["id"], r["user_id"], r.get("ai_pattern", ""),
             r.get("ai_weakness", ""), r.get("ai_advice", ""),
             r.get("weekly_message", ""), r.get("weekly_at"),
             r.get("generated_at")),
        )
    return len(rows)


def _migrate_credit_logs(src, cur):
    rows = sqlite_rows(src, "SELECT * FROM credit_logs")
    for r in rows:
        cur.execute(
            """INSERT INTO credit_logs (id, user_id, amount, reason, created_at)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING""",
            (r["id"], r["user_id"], r["amount"],
             r.get("reason"), r.get("created_at")),
        )
    return len(rows)


def _migrate_quiz_attempts(src, cur):
    rows = sqlite_rows(src, "SELECT * FROM quiz_attempts")
    for r in rows:
        cur.execute(
            """INSERT INTO quiz_attempts (id, user_id, question_id, is_correct, answered_at)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING""",
            (r["id"], r["user_id"], r["question_id"],
             r["is_correct"], r.get("answered_at")),
        )
    return len(rows)


if __name__ == "__main__":
    migrate()
