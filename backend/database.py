import sqlite3
import hashlib
import base64
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "app", "data", "app.db"),
)


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row) -> dict:
    """sqlite3.Row → dict. image_data BLOB은 base64 문자열로 변환."""
    if row is None:
        return None
    d = dict(row)
    if "image_data" in d and d["image_data"]:
        d["image_data"] = base64.b64encode(d["image_data"]).decode("utf-8")
    return d


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT NOT NULL,
            answer TEXT,
            image_data BLOB,
            image_mime TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS user_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            question TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            solution TEXT,
            embedding TEXT,
            image_data BLOB,
            image_mime TEXT,
            exam_year INTEGER,
            exam_round INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            memo TEXT NOT NULL DEFAULT '',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            UNIQUE (user_id, session_id)
        );

        CREATE TABLE IF NOT EXISTS exam_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exam_year INTEGER NOT NULL,
            exam_round INTEGER NOT NULL,
            problem_id INTEGER NOT NULL,
            user_answer TEXT,
            is_correct INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (problem_id) REFERENCES problems(id)
        );

        CREATE TABLE IF NOT EXISTS notebook_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            notebook_session_id INTEGER NOT NULL,
            messages TEXT NOT NULL DEFAULT '[]',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (notebook_session_id) REFERENCES sessions(id),
            UNIQUE(user_id, notebook_session_id)
        );

        CREATE TABLE IF NOT EXISTS learning_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            ai_pattern TEXT NOT NULL DEFAULT '',
            ai_advice  TEXT NOT NULL DEFAULT '',
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    # 기존 DB 마이그레이션 (컬럼 없을 때만 추가)
    migrations = [
        "ALTER TABLE sessions  ADD COLUMN embedding TEXT",
        "ALTER TABLE problems  ADD COLUMN image_data BLOB",
        "ALTER TABLE problems  ADD COLUMN image_mime TEXT",
        "ALTER TABLE problems  ADD COLUMN solution TEXT",
        "ALTER TABLE problems  ADD COLUMN correct_answer TEXT",
        "ALTER TABLE problems  ADD COLUMN exam_year INTEGER",
        "ALTER TABLE problems  ADD COLUMN exam_round INTEGER",
        "ALTER TABLE memos     ADD COLUMN rating INTEGER DEFAULT 3",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# =============================================================
# 유저
# =============================================================
def create_user(username: str, password: str) -> bool:
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hash_password(password)),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def get_user_by_credentials(username: str, password: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, hash_password(password)),
    ).fetchone()
    conn.close()
    return row_to_dict(row)


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
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
    cur = conn.execute(
        "INSERT INTO sessions (user_id, question, answer, image_data, image_mime) VALUES (?, ?, ?, ?, ?)",
        (user_id, question, answer, image_data, image_mime),
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id


def get_sessions(user_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (user_id,),
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_all_sessions_for_summary(user_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_sessions_last_week(user_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM sessions WHERE user_id = ?
           AND created_at >= datetime('now', '-7 days')
           ORDER BY created_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


# =============================================================
# 메모 / 오답노트
# =============================================================
def get_sessions_with_memo(user_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT s.*, m.memo
           FROM sessions s
           INNER JOIN memos m ON m.session_id = s.id AND m.user_id = s.user_id
           WHERE s.user_id = ?
             AND (m.memo != '' OR s.question LIKE '[오답노트]%' OR s.question LIKE '[모의고사]%')
           ORDER BY s.created_at ASC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def save_memo(user_id: int, session_id: int, memo: str):
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM memos WHERE user_id = ? AND session_id = ?",
        (user_id, session_id),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE memos SET memo = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND session_id = ?",
            (memo, user_id, session_id),
        )
    else:
        conn.execute(
            "INSERT INTO memos (user_id, session_id, memo) VALUES (?, ?, ?)",
            (user_id, session_id, memo),
        )
    conn.commit()
    conn.close()


def get_memo(user_id: int, session_id: int) -> str:
    conn = get_conn()
    row = conn.execute(
        "SELECT memo FROM memos WHERE user_id = ? AND session_id = ?",
        (user_id, session_id),
    ).fetchone()
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
    cur = conn.execute(
        "INSERT INTO sessions (user_id, question, answer, image_data, image_mime) VALUES (?, ?, ?, ?, ?)",
        (user_id, f"[오답노트] {question}", answer, image_data, image_mime),
    )
    session_id = cur.lastrowid
    conn.execute(
        "INSERT INTO memos (user_id, session_id, memo) VALUES (?, ?, ?)",
        (user_id, session_id, memo),
    )
    conn.commit()
    conn.close()
    return session_id


def update_notebook_entry(session_id: int, user_id: int, question: str, answer: str):
    conn = get_conn()
    conn.execute(
        "UPDATE sessions SET question = ?, answer = ? WHERE id = ? AND user_id = ?",
        (f"[오답노트] {question}", answer, session_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_notebook_entry(session_id: int, user_id: int):
    conn = get_conn()
    conn.execute(
        "DELETE FROM memos WHERE session_id = ? AND user_id = ?",
        (session_id, user_id),
    )
    conn.execute(
        "DELETE FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    conn.commit()
    conn.close()


# =============================================================
# 학습 요약
# =============================================================
def get_user_summaries(user_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, summary, created_at FROM user_summaries WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_user_summary(user_id: int, summary: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO user_summaries (user_id, summary) VALUES (?, ?)",
        (user_id, summary),
    )
    conn.commit()
    conn.close()


# =============================================================
# 문제은행
# =============================================================
def get_all_problems() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM problems ORDER BY id").fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_problems_by_round(exam_year: int, exam_round: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM problems WHERE exam_year = ? AND exam_round = ? ORDER BY id",
        (exam_year, exam_round),
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_exam_rounds() -> list[dict]:
    """사용 가능한 모의고사 회차 목록 반환."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT exam_year, exam_round, COUNT(*) as problem_count
           FROM problems
           WHERE exam_year IS NOT NULL AND exam_round IS NOT NULL
           GROUP BY exam_year, exam_round
           ORDER BY exam_year DESC, exam_round DESC""",
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_problem_solution(problem_id: int, solution: str, correct_answer: str = None):
    conn = get_conn()
    conn.execute(
        "UPDATE problems SET solution = ?, correct_answer = ? WHERE id = ?",
        (solution, correct_answer, problem_id),
    )
    conn.commit()
    conn.close()


def update_problem_embedding(problem_id: int, embedding_json: str):
    conn = get_conn()
    conn.execute(
        "UPDATE problems SET embedding = ? WHERE id = ?",
        (embedding_json, problem_id),
    )
    conn.commit()
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
    cur = conn.execute(
        """INSERT INTO exam_attempts
           (user_id, exam_year, exam_round, problem_id, user_answer, is_correct)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, exam_year, exam_round, problem_id, user_answer, int(is_correct)),
    )
    attempt_id = cur.lastrowid
    conn.commit()
    conn.close()
    return attempt_id


def auto_add_wrong_to_notebook(
    user_id: int,
    problem: dict,
    user_answer: str,
) -> int:
    """오답을 자동으로 오답노트에 추가. 세션 + 빈 메모 생성."""
    image_data = None
    if problem.get("image_data"):
        image_data = base64.b64decode(problem["image_data"])
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO sessions (user_id, question, answer, image_data, image_mime) VALUES (?, ?, ?, ?, ?)",
        (
            user_id,
            f"[모의고사] {problem['question']}",
            problem.get("solution") or "",
            image_data,
            problem.get("image_mime"),
        ),
    )
    session_id = cur.lastrowid
    conn.execute(
        "INSERT INTO memos (user_id, session_id, memo) VALUES (?, ?, ?)",
        (user_id, session_id, ""),
    )
    conn.commit()
    conn.close()
    return session_id


# =============================================================
# 오답노트 AI 토론 채팅 저장
# =============================================================
def get_notebook_chat(user_id: int, notebook_session_id: int) -> list:
    import json
    conn = get_conn()
    row = conn.execute(
        "SELECT messages FROM notebook_chats WHERE user_id = ? AND notebook_session_id = ?",
        (user_id, notebook_session_id),
    ).fetchone()
    conn.close()
    return json.loads(row["messages"]) if row else []


def get_learning_report(user_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT ai_pattern, ai_advice, generated_at FROM learning_reports WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_learning_report(user_id: int, ai_pattern: str, ai_advice: str):
    conn = get_conn()
    conn.execute(
        """INSERT INTO learning_reports (user_id, ai_pattern, ai_advice, generated_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(user_id)
           DO UPDATE SET ai_pattern = excluded.ai_pattern,
                         ai_advice  = excluded.ai_advice,
                         generated_at = CURRENT_TIMESTAMP""",
        (user_id, ai_pattern, ai_advice),
    )
    conn.commit()
    conn.close()


def save_notebook_chat(user_id: int, notebook_session_id: int, messages: list):
    import json
    conn = get_conn()
    conn.execute(
        """INSERT INTO notebook_chats (user_id, notebook_session_id, messages, updated_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(user_id, notebook_session_id)
           DO UPDATE SET messages = excluded.messages, updated_at = CURRENT_TIMESTAMP""",
        (user_id, notebook_session_id, json.dumps(messages, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
