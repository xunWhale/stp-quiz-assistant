"""Storage layer for user scores, quiz history, and wrong question books using SQLite."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from stp_quiz.models import PaperScoreReport, UserRecord, WrongRecord


DEFAULT_DB_PATH = Path.home() / ".stp_quiz" / "stp_quiz.db"


class Storage:
    """SQLite-backed storage with JSON export/import support."""

    def __init__(self, db_path: Optional[str | Path] = None):
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Users table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    nickname TEXT NOT NULL,
                    total_score REAL DEFAULT 0.0,
                    total_quizzes INTEGER DEFAULT 0,
                    passed_quizzes INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            # Wrong records table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS wrong_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    question_title TEXT NOT NULL,
                    user_answer TEXT NOT NULL,
                    score REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    knowledge_tag TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
                """
            )
            # Quiz history log
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS quiz_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    question_title TEXT NOT NULL,
                    user_answer TEXT NOT NULL,
                    score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    is_retest INTEGER NOT NULL DEFAULT 0,
                    details TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            # Full Exam Papers table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS exam_papers (
                    paper_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    nickname TEXT NOT NULL,
                    total_score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    details TEXT NOT NULL,
                    weak_tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
                """
            )
            conn.commit()

            # Ensure columns exist if table was created in an earlier schema
            self._ensure_column(cursor, "wrong_records", "knowledge_tag", "TEXT DEFAULT ''")
            self._ensure_column(cursor, "quiz_history", "details", "TEXT DEFAULT ''")
            conn.commit()

    @staticmethod
    def _ensure_column(cursor: sqlite3.Cursor, table: str, column: str, col_type: str) -> None:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if column not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    def get_or_create_user(self, user_id: str, nickname: Optional[str] = None) -> UserRecord:
        user_id = str(user_id).strip()
        nickname = (nickname or user_id).strip()
        now = datetime.now().isoformat()

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return UserRecord(
                    user_id=row["user_id"],
                    nickname=row["nickname"],
                    total_score=row["total_score"],
                    total_quizzes=row["total_quizzes"],
                    passed_quizzes=row["passed_quizzes"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

            cursor.execute(
                """
                INSERT INTO users (user_id, nickname, total_score, total_quizzes, passed_quizzes, created_at, updated_at)
                VALUES (?, ?, 0.0, 0, 0, ?, ?)
                """,
                (user_id, nickname, now, now),
            )
            conn.commit()
            return UserRecord(
                user_id=user_id,
                nickname=nickname,
                total_score=0.0,
                total_quizzes=0,
                passed_quizzes=0,
                created_at=now,
                updated_at=now,
            )

    def record_quiz_result(
        self,
        user_id: str,
        question_id: str,
        question_title: str,
        user_answer: str,
        score: float,
        passed: bool,
        is_retest: bool = False,
        nickname: Optional[str] = None,
        knowledge_tag: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> Tuple[UserRecord, Optional[WrongRecord]]:
        now = datetime.now().isoformat()
        user = self.get_or_create_user(user_id, nickname)
        details_str = json.dumps(details, ensure_ascii=False) if details else ""

        with self._get_conn() as conn:
            cursor = conn.cursor()

            # Record in history
            cursor.execute(
                """
                INSERT INTO quiz_history (user_id, question_id, question_title, user_answer, score, passed, is_retest, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, question_id, question_title, user_answer, score, 1 if passed else 0, 1 if is_retest else 0, details_str, now),
            )

            # Update user stats
            new_total_score = user.total_score + score
            new_total_quizzes = user.total_quizzes + 1
            new_passed_quizzes = user.passed_quizzes + (1 if passed else 0)

            cursor.execute(
                """
                UPDATE users
                SET total_score = ?, total_quizzes = ?, passed_quizzes = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (new_total_score, new_total_quizzes, new_passed_quizzes, now, user_id),
            )

            wrong_rec = None
            if not passed and not is_retest:
                # Add to wrong records
                cursor.execute(
                    """
                    INSERT INTO wrong_records (user_id, question_id, question_title, user_answer, score, status, knowledge_tag, created_at)
                    VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                    """,
                    (user_id, question_id, question_title, user_answer, score, knowledge_tag, now),
                )
                rec_id = cursor.lastrowid
                wrong_rec = WrongRecord(
                    id=rec_id,
                    user_id=user_id,
                    question_id=question_id,
                    question_title=question_title,
                    user_answer=user_answer,
                    score=score,
                    status="pending",
                    knowledge_tag=knowledge_tag,
                    created_at=now,
                )

            conn.commit()

        updated_user = self.get_or_create_user(user_id, nickname)
        return updated_user, wrong_rec

    def record_paper_result(self, report: PaperScoreReport) -> None:
        """Persist a full paper score report."""
        user = self.get_or_create_user(report.user_id, report.nickname)
        details_str = json.dumps(report.item_results, ensure_ascii=False)
        weak_tags_str = json.dumps(report.weak_tags, ensure_ascii=False)

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO exam_papers (paper_id, user_id, nickname, total_score, max_score, passed, details, weak_tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.paper_id,
                    report.user_id,
                    report.nickname,
                    report.total_score,
                    report.max_score,
                    1 if report.passed else 0,
                    details_str,
                    weak_tags_str,
                    report.created_at,
                ),
            )
            conn.commit()

    def get_user_papers(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve historical paper score records for a user."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM exam_papers WHERE user_id = ? ORDER BY created_at DESC",
                (str(user_id).strip(),),
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append(
                    {
                        "paper_id": r["paper_id"],
                        "user_id": r["user_id"],
                        "nickname": r["nickname"],
                        "total_score": r["total_score"],
                        "max_score": r["max_score"],
                        "passed": bool(r["passed"]),
                        "details": json.loads(r["details"]) if r["details"] else [],
                        "weak_tags": json.loads(r["weak_tags"]) if r["weak_tags"] else [],
                        "created_at": r["created_at"],
                    }
                )
            return results

    def get_user_weak_tags(self, user_id: str) -> List[str]:
        """Collect all untamed weak tags from pending wrong records for user."""
        wrongs = self.get_pending_wrong_records(user_id)
        tags = []
        for w in wrongs:
            if w.knowledge_tag and w.knowledge_tag not in tags:
                tags.append(w.knowledge_tag)
        return tags

    def get_user_audit(self, user_id: str) -> Dict[str, Any]:
        """Get full audit summary of a user: profile, stats, pending wrongs, weak tags, paper count."""
        user = self.get_or_create_user(user_id)
        pending_wrongs = self.get_pending_wrong_records(user_id)
        weak_tags = self.get_user_weak_tags(user_id)
        papers = self.get_user_papers(user_id)

        return {
            "user_id": user.user_id,
            "nickname": user.nickname,
            "total_score": user.total_score,
            "total_quizzes": user.total_quizzes,
            "passed_quizzes": user.passed_quizzes,
            "pass_rate": user.pass_rate,
            "pending_wrong_count": len(pending_wrongs),
            "pending_wrongs": pending_wrongs,
            "weak_tags": weak_tags,
            "papers_count": len(papers),
            "latest_papers": papers[:3],
        }

    def get_pending_wrong_records(self, user_id: Optional[str] = None) -> List[WrongRecord]:
        query = "SELECT * FROM wrong_records WHERE status = 'pending'"
        params: List[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(str(user_id).strip())
        query += " ORDER BY id ASC"

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [
                WrongRecord(
                    id=row["id"],
                    user_id=row["user_id"],
                    question_id=row["question_id"],
                    question_title=row["question_title"],
                    user_answer=row["user_answer"],
                    score=row["score"],
                    status=row["status"],
                    knowledge_tag=row["knowledge_tag"] if "knowledge_tag" in row.keys() else "",
                    created_at=row["created_at"],
                    resolved_at=row["resolved_at"],
                )
                for row in rows
            ]

    def resolve_wrong_record(self, record_id: int, retest_score: float) -> bool:
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE wrong_records
                SET status = 'resolved', resolved_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (now, record_id),
            )
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def get_leaderboard(self, limit: int = 10) -> List[UserRecord]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM users
                ORDER BY total_score DESC, passed_quizzes DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                UserRecord(
                    user_id=row["user_id"],
                    nickname=row["nickname"],
                    total_score=row["total_score"],
                    total_quizzes=row["total_quizzes"],
                    passed_quizzes=row["passed_quizzes"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def export_json(self, target_path: str | Path) -> None:
        target = Path(target_path)
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users")
            users = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT * FROM wrong_records")
            wrong_records = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT * FROM quiz_history")
            history = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT * FROM exam_papers")
            papers = [dict(row) for row in cursor.fetchall()]

        data = {
            "users": users,
            "wrong_records": wrong_records,
            "quiz_history": history,
            "exam_papers": papers,
            "exported_at": datetime.now().isoformat(),
        }

        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_json(self, source_path: str | Path) -> None:
        with open(source_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        with self._get_conn() as conn:
            cursor = conn.cursor()

            for u in data.get("users", []):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO users (user_id, nickname, total_score, total_quizzes, passed_quizzes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (u["user_id"], u["nickname"], u["total_score"], u["total_quizzes"], u["passed_quizzes"], u["created_at"], u["updated_at"]),
                )

            for w in data.get("wrong_records", []):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO wrong_records (id, user_id, question_id, question_title, user_answer, score, status, knowledge_tag, created_at, resolved_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (w["id"], w["user_id"], w["question_id"], w["question_title"], w["user_answer"], w["score"], w["status"], w.get("knowledge_tag", ""), w["created_at"], w.get("resolved_at")),
                )

            for h in data.get("quiz_history", []):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO quiz_history (id, user_id, question_id, question_title, user_answer, score, passed, is_retest, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (h["id"], h["user_id"], h["question_id"], h["question_title"], h["user_answer"], h["score"], h["passed"], h.get("is_retest", 0), h.get("details", ""), h["created_at"]),
                )

            for p in data.get("exam_papers", []):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO exam_papers (paper_id, user_id, nickname, total_score, max_score, passed, details, weak_tags, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (p["paper_id"], p["user_id"], p["nickname"], p["total_score"], p["max_score"], p["passed"], p["details"], p["weak_tags"], p["created_at"]),
                )

            conn.commit()


# Tracker alias
QuizTracker = Storage
Tracker = Storage
