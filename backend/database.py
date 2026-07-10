import json
import hashlib
import base64
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_SQLITE = not DATABASE_URL or DATABASE_URL.startswith("sqlite")
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "local.db")


def get_conn():
    if USE_SQLITE:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    else:
        import psycopg2
        import psycopg2.extras
        return psycopg2.connect(DATABASE_URL)


def _cursor(conn):
    if USE_SQLITE:
        return conn.cursor()
    else:
        import psycopg2.extras
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def row_to_dict(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    if "image_data" in d and d["image_data"]:
        if isinstance(d["image_data"], (bytes, bytearray)):
            d["image_data"] = base64.b64encode(bytes(d["image_data"])).decode("utf-8")
    return d


def _fix(sql: str) -> str:
    if not USE_SQLITE:
        return sql
    import re
    sql = sql.replace("%s", "?")
    sql = re.sub(r'\bSERIAL PRIMARY KEY\b', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql)
    sql = re.sub(r'\bBYTEA\b', 'BLOB', sql, flags=re.IGNORECASE)
    sql = re.sub(r"NOW\(\)\s*-\s*INTERVAL\s*'(\d+)\s*days'", r"datetime('now', '-\1 days')", sql)
    sql = re.sub(r"NOW\(\)", "datetime('now')", sql)
    return sql


def _insert_returning(cur, conn, sql: str, params: tuple):
    """INSERT ... RETURNING id 처리 — SQLite는 lastrowid 사용."""
    if USE_SQLITE:
        sql = _fix(sql.split("RETURNING")[0].strip())
        cur.execute(sql, params)
        return cur.lastrowid
    else:
        cur.execute(sql, params)
        return cur.fetchone()["id"]


def _upsert(cur, table: str, conflict_cols: list, data: dict):
    """ON CONFLICT DO UPDATE 처리."""
    cols = list(data.keys())
    vals = list(data.values())
    ph = "?" if USE_SQLITE else "%s"
    placeholders = ", ".join([ph] * len(cols))
    col_str = ", ".join(cols)

    if USE_SQLITE:
        update_str = ", ".join(
            f"{c} = excluded.{c}" for c in cols if c not in conflict_cols
        )
        conflict_str = ", ".join(conflict_cols)
        sql = f"""INSERT INTO {table} ({col_str}) VALUES ({placeholders})
                  ON CONFLICT({conflict_str}) DO UPDATE SET {update_str}"""
    else:
        update_str = ", ".join(
            f"{c} = EXCLUDED.{c}" for c in cols if c not in conflict_cols
        )
        conflict_str = ", ".join(conflict_cols)
        sql = f"""INSERT INTO {table} ({col_str}) VALUES ({placeholders})
                  ON CONFLICT ({conflict_str}) DO UPDATE SET {update_str}"""
    cur.execute(sql, vals)


def init_db():
    conn = get_conn()
    cur = _cursor(conn)

    cur.execute(_fix("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            credits INTEGER NOT NULL DEFAULT 30,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    cur.execute(_fix("""
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            question TEXT NOT NULL,
            answer TEXT,
            image_data BYTEA,
            image_mime TEXT,
            embedding TEXT,
            problem_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    cur.execute(_fix("""
        CREATE TABLE IF NOT EXISTS problems (
            id SERIAL PRIMARY KEY,
            topic TEXT NOT NULL,
            question TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            solution TEXT,
            correct_answer TEXT,
            concept TEXT,
            question_text TEXT,
            embedding TEXT,
            image_data BYTEA,
            image_mime TEXT,
            exam_year INTEGER,
            exam_round INTEGER,
            exam_type TEXT DEFAULT 'civil',
            ncs_agency TEXT,
            ncs_domain TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    cur.execute(_fix("""
        CREATE TABLE IF NOT EXISTS memos (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            memo TEXT NOT NULL DEFAULT '',
            rating INTEGER DEFAULT 3,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, session_id)
        )
    """))

    cur.execute(_fix("""
        CREATE TABLE IF NOT EXISTS exam_attempts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            exam_year INTEGER NOT NULL,
            exam_round INTEGER NOT NULL,
            problem_id INTEGER NOT NULL REFERENCES problems(id),
            user_answer TEXT,
            is_correct INTEGER DEFAULT 0,
            exam_type TEXT DEFAULT 'civil',
            ncs_agency TEXT,
            ncs_domain TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    cur.execute(_fix("""
        CREATE TABLE IF NOT EXISTS notebook_chats (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            notebook_session_id INTEGER NOT NULL REFERENCES sessions(id),
            mode TEXT NOT NULL DEFAULT 'teacher',
            messages TEXT NOT NULL DEFAULT '[]',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, notebook_session_id, mode)
        )
    """))

    cur.execute(_fix("""
        CREATE TABLE IF NOT EXISTS learning_reports (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            ai_pattern TEXT NOT NULL DEFAULT '',
            ai_weakness TEXT NOT NULL DEFAULT '',
            ai_advice TEXT NOT NULL DEFAULT '',
            weekly_message TEXT NOT NULL DEFAULT '',
            weekly_at TIMESTAMP,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    cur.execute(_fix("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            question_id TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    conn.commit()
    cur.close()
    conn.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# =============================================================
# 유저
# =============================================================
def create_user(username: str, password: str) -> bool:
    try:
        conn = get_conn()
        cur = _cursor(conn)
        cur.execute(
            _fix("INSERT INTO users (username, password) VALUES (%s, %s)"),
            (username, hash_password(password)),
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception:
        return False


def get_user_by_credentials(username: str, password: str) -> dict | None:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("SELECT * FROM users WHERE username = %s AND password = %s"),
        (username, hash_password(password)),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row_to_dict(row)


def get_all_user_ids() -> list[int]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute("SELECT id FROM users")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r["id"] for r in rows]


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(_fix("SELECT * FROM users WHERE id = %s"), (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row_to_dict(row)


# =============================================================
# 세션 (히스토리)
# =============================================================
def save_session(
    user_id: int,
    question: str,
    answer: str,
    image_data: bytes = None,
    image_mime: str = None,
) -> int:
    conn = get_conn()
    cur = _cursor(conn)
    session_id = _insert_returning(cur, conn,
        """INSERT INTO sessions (user_id, question, answer, image_data, image_mime)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (user_id, question, answer, image_data, image_mime),
    )
    conn.commit()
    cur.close()
    conn.close()
    return session_id


def get_sessions(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("SELECT * FROM sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 50"),
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_all_sessions_for_summary(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("SELECT * FROM sessions WHERE user_id = %s ORDER BY created_at DESC"),
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_sessions_last_week(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("""SELECT * FROM sessions WHERE user_id = %s
           AND created_at >= NOW() - INTERVAL '7 days'
           ORDER BY created_at DESC"""),
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row_to_dict(r) for r in rows]


# =============================================================
# 메모 / 오답노트
# =============================================================
def get_sessions_with_memo(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("""SELECT s.*, m.memo,
                  p.question AS problem_question,
                  p.question_text AS problem_question_text,
                  p.correct_answer AS problem_correct_answer,
                  p.concept AS problem_concept
           FROM sessions s
           INNER JOIN memos m ON m.session_id = s.id AND m.user_id = s.user_id
           LEFT JOIN problems p ON p.id = s.problem_id
           WHERE s.user_id = %s
             AND (m.memo != '' OR s.question LIKE '[오답노트]%%' OR s.question LIKE '[모의고사]%%')
           ORDER BY s.created_at DESC"""),
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row_to_dict(r) for r in rows]


def save_memo(user_id: int, session_id: int, memo: str):
    conn = get_conn()
    cur = _cursor(conn)
    _upsert(cur, "memos", ["user_id", "session_id"], {
        "user_id": user_id,
        "session_id": session_id,
        "memo": memo,
        "updated_at": "CURRENT_TIMESTAMP",
    })
    conn.commit()
    cur.close()
    conn.close()


def get_memo(user_id: int, session_id: int) -> str:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("SELECT memo FROM memos WHERE user_id = %s AND session_id = %s"),
        (user_id, session_id),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["memo"] if row else ""


def add_to_notebook(
    user_id: int,
    question: str,
    answer: str = "",
    memo: str = "",
    image_data: bytes = None,
    image_mime: str = None,
) -> int:
    conn = get_conn()
    cur = _cursor(conn)
    session_id = _insert_returning(cur, conn,
        """INSERT INTO sessions (user_id, question, answer, image_data, image_mime)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (user_id, f"[오답노트] {question}", answer, image_data, image_mime),
    )
    cur.execute(
        _fix("INSERT INTO memos (user_id, session_id, memo) VALUES (%s, %s, %s)"),
        (user_id, session_id, memo),
    )
    conn.commit()
    cur.close()
    conn.close()
    return session_id


def update_notebook_entry(session_id: int, user_id: int, question: str, answer: str):
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("UPDATE sessions SET question = %s, answer = %s WHERE id = %s AND user_id = %s"),
        (f"[오답노트] {question}", answer, session_id, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def delete_notebook_entry(session_id: int, user_id: int):
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("DELETE FROM memos WHERE session_id = %s AND user_id = %s"),
        (session_id, user_id),
    )
    cur.execute(
        _fix("DELETE FROM sessions WHERE id = %s AND user_id = %s"),
        (session_id, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


# =============================================================
# 문제은행
# =============================================================
def get_all_problems() -> list[dict]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute("SELECT * FROM problems ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_problems_by_round(exam_year: int, exam_round: int) -> list[dict]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("SELECT * FROM problems WHERE exam_year = %s AND exam_round = %s ORDER BY id"),
        (exam_year, exam_round),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_problems_by_ncs(agency: str, exam_year: int, domain: str) -> list[dict]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("""SELECT * FROM problems
           WHERE exam_type = 'ncs' AND ncs_agency = %s AND exam_year = %s AND ncs_domain = %s
           ORDER BY id"""),
        (agency, exam_year, domain),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_exam_rounds() -> list[dict]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        """SELECT exam_year, exam_round, COUNT(*) as problem_count
           FROM problems
           WHERE exam_year IS NOT NULL AND exam_round IS NOT NULL
             AND (exam_type IS NULL OR exam_type = 'civil')
           GROUP BY exam_year, exam_round
           ORDER BY exam_year DESC, exam_round DESC""",
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_ncs_list() -> list[dict]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        """SELECT ncs_agency, exam_year, ncs_domain, COUNT(*) as problem_count
           FROM problems
           WHERE exam_type = 'ncs'
             AND ncs_agency IS NOT NULL
             AND exam_year IS NOT NULL
             AND ncs_domain IS NOT NULL
           GROUP BY ncs_agency, exam_year, ncs_domain
           ORDER BY ncs_agency, exam_year DESC, ncs_domain""",
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def save_exam_attempt_ncs(user_id: int, agency: str, exam_year: int, domain: str,
                          problem_id: int, user_answer: str, is_correct: bool):
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("""INSERT INTO exam_attempts
           (user_id, exam_year, exam_round, problem_id, user_answer, is_correct,
            exam_type, ncs_agency, ncs_domain)
           VALUES (%s, %s, 0, %s, %s, %s, 'ncs', %s, %s)"""),
        (user_id, exam_year, problem_id, user_answer, int(is_correct), agency, domain),
    )
    conn.commit()
    cur.close()
    conn.close()


def update_problem_solution(problem_id: int, solution: str, correct_answer: str = None):
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("UPDATE problems SET solution = %s, correct_answer = %s WHERE id = %s"),
        (solution, correct_answer, problem_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def update_problem_embedding(problem_id: int, embedding_json: str):
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("UPDATE problems SET embedding = %s WHERE id = %s"),
        (embedding_json, problem_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def update_problem_question_text(problem_id: int, question_text: str):
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("UPDATE problems SET question_text = %s WHERE id = %s"),
        (question_text, problem_id),
    )
    conn.commit()
    cur.close()
    conn.close()


# =============================================================
# 모의고사
# =============================================================
def save_exam_attempt(
    user_id: int,
    exam_year: int,
    exam_round: int,
    problem_id: int,
    user_answer: str,
    is_correct: bool,
) -> int:
    conn = get_conn()
    cur = _cursor(conn)
    attempt_id = _insert_returning(cur, conn,
        """INSERT INTO exam_attempts
           (user_id, exam_year, exam_round, problem_id, user_answer, is_correct)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
        (user_id, exam_year, exam_round, problem_id, user_answer, int(is_correct)),
    )
    conn.commit()
    cur.close()
    conn.close()
    return attempt_id


def _notebook_label(problem: dict) -> str:
    if problem.get("ncs_agency"):
        label = f"[모의고사] {problem['ncs_agency']} {problem['exam_year']}년 {problem['ncs_domain']}"
        actual_q = (problem.get("question") or "").strip()
        return f"{label}\n{actual_q}" if actual_q else label
    else:
        return f"[모의고사] {problem['question']}"


def auto_add_wrong_to_notebook(
    user_id: int,
    problem: dict,
    user_answer: str,
) -> int:
    image_data = None
    if problem.get("image_data"):
        image_data = base64.b64decode(problem["image_data"])
    conn = get_conn()
    cur = _cursor(conn)
    session_id = _insert_returning(cur, conn,
        """INSERT INTO sessions (user_id, question, answer, image_data, image_mime, problem_id)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
        (
            user_id,
            _notebook_label(problem),
            problem.get("solution") or "",
            image_data,
            problem.get("image_mime"),
            problem.get("id"),
        ),
    )
    cur.execute(
        _fix("INSERT INTO memos (user_id, session_id, memo) VALUES (%s, %s, %s)"),
        (user_id, session_id, ""),
    )
    conn.commit()
    cur.close()
    conn.close()
    return session_id


# =============================================================
# 오답노트 AI 토론 채팅 저장
# =============================================================
def get_notebook_chat(user_id: int, notebook_session_id: int, mode: str = "teacher") -> list:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("SELECT messages FROM notebook_chats WHERE user_id = %s AND notebook_session_id = %s AND mode = %s"),
        (user_id, notebook_session_id, mode),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return json.loads(row["messages"]) if row else []


def save_notebook_chat(user_id: int, notebook_session_id: int, messages: list, mode: str = "teacher"):
    conn = get_conn()
    cur = _cursor(conn)
    _upsert(cur, "notebook_chats", ["user_id", "notebook_session_id", "mode"], {
        "user_id": user_id,
        "notebook_session_id": notebook_session_id,
        "mode": mode,
        "messages": json.dumps(messages, ensure_ascii=False),
        "updated_at": "CURRENT_TIMESTAMP",
    })
    conn.commit()
    cur.close()
    conn.close()


# =============================================================
# 학습일지
# =============================================================
def get_learning_report(user_id: int) -> dict | None:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("""SELECT ai_pattern, ai_weakness, ai_advice, generated_at FROM learning_reports
           WHERE user_id = %s ORDER BY generated_at DESC LIMIT 1"""),
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def save_learning_report(user_id: int, ai_pattern: str, ai_advice: str, ai_weakness: str = ""):
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("""INSERT INTO learning_reports (user_id, ai_pattern, ai_weakness, ai_advice, generated_at)
           VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)"""),
        (user_id, ai_pattern, ai_weakness, ai_advice),
    )
    conn.commit()
    cur.close()
    conn.close()


# =============================================================
# 크레딧
# =============================================================
def get_credits(user_id: int) -> int:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(_fix("SELECT credits FROM users WHERE id = %s"), (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["credits"] if row else 0


def charge_credits(user_id: int, amount: int, reason: str = "관리자 충전"):
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(_fix("UPDATE users SET credits = credits + %s WHERE id = %s"), (amount, user_id))
    conn.commit()
    cur.close()
    conn.close()


def deduct_credits(user_id: int, amount: int, reason: str) -> bool:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(_fix("SELECT credits FROM users WHERE id = %s"), (user_id,))
    row = cur.fetchone()
    if not row or row["credits"] < amount:
        cur.close()
        conn.close()
        return False
    cur.execute(_fix("UPDATE users SET credits = credits - %s WHERE id = %s"), (amount, user_id))
    conn.commit()
    cur.close()
    conn.close()
    return True


def get_all_users_credits() -> list[dict]:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute("SELECT id, username, credits, created_at FROM users ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


# =============================================================
# OX 퀴즈 결과
# =============================================================
def save_quiz_attempt(user_id: int, question_id: str, is_correct: bool):
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("INSERT INTO quiz_attempts (user_id, question_id, is_correct) VALUES (%s, %s, %s)"),
        (user_id, question_id, int(is_correct)),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_quiz_stats(user_id: int) -> dict:
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(
        _fix("""SELECT question_id,
                  SUM(CASE WHEN is_correct=0 THEN 1 ELSE 0 END) AS wrong,
                  SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) AS correct
           FROM quiz_attempts
           WHERE user_id = %s
           GROUP BY question_id"""),
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {r["question_id"]: {"wrong": r["wrong"], "correct": r["correct"]} for r in rows}
