"""
Async SQLite database manager for the English Learning Bot.
نسخه نهایی - ضد قطعی با asyncio.Lock + پشتیبانی از Category
"""
import asyncio
import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import aiosqlite
from config import DB_PATH

logger = logging.getLogger(__name__)


class Database:
    def __init__(self) -> None:
        self.db_path: str = DB_PATH
        self.db: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()  # ✅ جلوگیری از Race Condition

    async def connect(self) -> None:
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA foreign_keys = ON")

    async def close(self) -> None:
        if self.db:
            await self.db.close()
            self.db = None

    async def _ensure_connected(self) -> None:
        """اطمینان از برقرار بودن اتصال با استفاده از Lock"""
        async with self._lock:
            if self.db is None:
                logger.info("Reconnecting to database...")
                await self.connect()

    async def init_db(self) -> None:
        await self.connect()
        await self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS whitelist (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS access_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                request_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_time DATETIME
            );
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                unit INTEGER,
                source TEXT,
                category TEXT,
                type TEXT,
                title TEXT,
                audio_file_id TEXT,
                content TEXT,
                questions TEXT,
                correct_answer TEXT,
                transcript TEXT,
                translation TEXT,
                vocabulary TEXT,
                grammar_notes TEXT,
                difficulty INTEGER DEFAULT 1,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audio_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_type TEXT,
                level TEXT,
                unit INTEGER,
                track_number TEXT,
                title TEXT,
                page_reference TEXT,
                type TEXT,
                audio_file_id TEXT,
                duration INTEGER,
                category TEXT DEFAULT 'main',
                transcript TEXT,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS video_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_type TEXT,
                level TEXT,
                unit INTEGER,
                track_number TEXT,
                title TEXT,
                page_reference TEXT,
                type TEXT,
                video_file_id TEXT,
                duration INTEGER,
                category TEXT DEFAULT 'main',
                transcript TEXT,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                resource_type TEXT,
                title TEXT,
                file_id TEXT,
                size_mb REAL,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                exercise_id INTEGER,
                score INTEGER,
                total_questions INTEGER,
                completed_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, exercise_id)
            );
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                current_level TEXT DEFAULT 'starter',
                streak_days INTEGER DEFAULT 0,
                last_active_date DATE,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await self.db.commit()
        logger.info("Database schema ensured with category columns.")

    async def setup_sample_data(self) -> None:
        pass

    @staticmethod
    def _row_to_dict(row: Optional[aiosqlite.Row]) -> Optional[Dict[str, Any]]:
        return dict(row) if row is not None else None

    @staticmethod
    def _decode_exercise(exercise: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if exercise is None:
            return None
        for field in ("questions", "content", "vocabulary"):
            value = exercise.get(field)
            if value:
                try:
                    exercise[field] = json.loads(value)
                except (TypeError, ValueError):
                    pass
        return exercise

    # ==================== Whitelist ====================
    async def is_in_whitelist(self, user_id: int) -> bool:
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                "SELECT 1 FROM whitelist WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row is not None
        except Exception as e:
            logger.error(f"Error checking whitelist for user {user_id}: {e}")
            return False

    async def add_to_whitelist(self, user_id: int, added_by: int) -> None:
        await self._ensure_connected()
        try:
            await self.db.execute(
                """INSERT INTO whitelist (user_id, added_by) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET added_by = excluded.added_by""",
                (user_id, added_by),
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error adding user {user_id} to whitelist: {e}")

    async def remove_from_whitelist(self, user_id: int) -> None:
        await self._ensure_connected()
        try:
            await self.db.execute("DELETE FROM whitelist WHERE user_id = ?", (user_id,))
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error removing user {user_id} from whitelist: {e}")

    # ==================== Access Requests ====================
    async def save_access_request(self, user_id: int, username: str, first_name: str, last_name: str) -> None:
        await self._ensure_connected()
        try:
            await self.db.execute(
                """INSERT INTO access_requests (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username, first_name = excluded.first_name,
                    last_name = excluded.last_name, status = 'pending',
                    request_time = CURRENT_TIMESTAMP, reviewed_by = NULL, reviewed_time = NULL""",
                (user_id, username, first_name, last_name),
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error saving access request for user {user_id}: {e}")

    async def update_request_status(self, user_id: int, status: str, reviewed_by: int) -> None:
        await self._ensure_connected()
        try:
            await self.db.execute(
                """UPDATE access_requests SET status = ?, reviewed_by = ?,
                reviewed_time = CURRENT_TIMESTAMP WHERE user_id = ?""",
                (status, reviewed_by, user_id),
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error updating request status for user {user_id}: {e}")

    async def get_request_by_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                "SELECT * FROM access_requests WHERE user_id = ?", (user_id,)
            )
            return self._row_to_dict(await cursor.fetchone())
        except Exception as e:
            logger.error(f"Error fetching access request for user {user_id}: {e}")
            return None

    async def get_pending_requests(self) -> List[Dict[str, Any]]:
        """دریافت تمام درخواست‌های در انتظار"""
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                "SELECT * FROM access_requests WHERE status = 'pending' ORDER BY request_time ASC"
            )
            return [dict(row) for row in await cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching pending requests: {e}")
            return []

    # ==================== Media by Category (جدید) ====================
    async def get_media_by_category(self, level: str, unit: int, category: str, media_type: str) -> List[Dict[str, Any]]:
        """دریافت ویس یا ویدیو بر اساس دسته‌بندی (Practical, Review, Listening, etc.)"""
        await self._ensure_connected()
        try:
            table = "video_tracks" if media_type == "video" else "audio_tracks"
            
            # ✅ اگر unit == 0 باشد، یعنی کاربر از منوی اصلی Level کلیک کرده و کل محتوای آن سطح را می‌خواهد
            if unit == 0:
                query = f"""
                    SELECT * FROM {table}
                    WHERE level = ? AND category = ? AND type = ?
                    ORDER BY unit ASC, track_number ASC
                """
                cursor = await self.db.execute(query, (level, category, media_type))
            else:
                # ✅ اگر unit مشخص باشد (مثلاً از داخل یک یونیت خاص)، فقط همان یونیت را فیلتر کن
                query = f"""
                    SELECT * FROM {table}
                    WHERE level = ? AND unit = ? AND category = ? AND type = ?
                    ORDER BY track_number ASC
                """
                cursor = await self.db.execute(query, (level, unit, category, media_type))
                
            return [dict(row) for row in await cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching media by category: {e}")
            return []
    # ==================== Legacy Audio/Video (برای سازگاری) ====================
    async def get_audio_tracks(self, level: str, unit: int, book_type: str) -> List[Dict[str, Any]]:
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                """SELECT * FROM audio_tracks
                WHERE level = ? AND unit = ? AND book_type = ? AND category = 'main'
                ORDER BY 
                    CAST(SUBSTR(track_number, 1, INSTR(track_number, '.') - 1) AS INTEGER),
                    CAST(SUBSTR(track_number, INSTR(track_number, '.') + 1) AS INTEGER)""",
                (level, unit, book_type),
            )
            return [dict(row) for row in await cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching audio tracks: {e}")
            return []

    async def get_audio_track(self, track_id: int) -> Optional[Dict[str, Any]]:
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                "SELECT * FROM audio_tracks WHERE id = ?", (track_id,)
            )
            return self._row_to_dict(await cursor.fetchone())
        except Exception as e:
            logger.error(f"Error fetching audio track {track_id}: {e}")
            return None

    async def get_video_tracks(self, level: str, unit: int, book_type: str) -> List[Dict[str, Any]]:
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                """SELECT * FROM video_tracks
                WHERE level = ? AND unit = ? AND book_type = ? AND category = 'main'
                ORDER BY 
                    CAST(SUBSTR(track_number, 1, INSTR(track_number, '.') - 1) AS INTEGER),
                    CAST(SUBSTR(track_number, INSTR(track_number, '.') + 1) AS INTEGER)""",
                (level, unit, book_type),
            )
            return [dict(row) for row in await cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching video tracks: {e}")
            return []

    async def get_video_track(self, track_id: int) -> Optional[Dict[str, Any]]:
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                "SELECT * FROM video_tracks WHERE id = ?", (track_id,)
            )
            return self._row_to_dict(await cursor.fetchone())
        except Exception as e:
            logger.error(f"Error fetching video track {track_id}: {e}")
            return None

    # ==================== Resources ====================
    async def get_resources_by_level(self, level: str) -> List[Dict[str, Any]]:
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                "SELECT * FROM resources WHERE level = ? ORDER BY id ASC", (level,)
            )
            return [dict(row) for row in await cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching resources for level={level}: {e}")
            return []

    async def get_resource(self, resource_id: int) -> Optional[Dict[str, Any]]:
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                "SELECT * FROM resources WHERE id = ?", (resource_id,)
            )
            return self._row_to_dict(await cursor.fetchone())
        except Exception as e:
            logger.error(f"Error fetching resource {resource_id}: {e}")
            return None

    # ==================== Exercises ====================
    async def get_exercises_by_level_unit(self, level: str, unit: int, source: str = None) -> List[Dict[str, Any]]:
        await self._ensure_connected()
        try:
            if source:
                cursor = await self.db.execute(
                    "SELECT * FROM exercises WHERE level = ? AND unit = ? AND source = ? ORDER BY id ASC",
                    (level, unit, source),
                )
            else:
                cursor = await self.db.execute(
                    "SELECT * FROM exercises WHERE level = ? AND unit = ? ORDER BY id ASC",
                    (level, unit),
                )
            return [self._decode_exercise(dict(row)) for row in await cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching exercises: {e}")
            return []

    async def get_exercise(self, exercise_id: int) -> Optional[Dict[str, Any]]:
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                "SELECT * FROM exercises WHERE id = ?", (exercise_id,)
            )
            return self._decode_exercise(self._row_to_dict(await cursor.fetchone()))
        except Exception as e:
            logger.error(f"Error fetching exercise {exercise_id}: {e}")
            return None

    # ==================== Progress & Users ====================
    async def get_user_streak(self, user_id: int) -> int:
        """✅ باگ رفع شد - دریافت streak کاربر"""
        await self._ensure_connected()
        try:
            cursor = await self.db.execute(
                "SELECT streak_days FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row["streak_days"] if row else 0
        except Exception as e:
            logger.error(f"Error fetching streak for user {user_id}: {e}")
            return 0

    async def get_user_progress(self, user_id: int, level: str = None) -> Dict[str, Any]:
        """✅ باگ رفع شد - دریافت پیشرفت کاربر"""
        await self._ensure_connected()
        try:
            if level:
                cursor = await self.db.execute(
                    """SELECT up.*, e.level AS exercise_level, e.title AS exercise_title
                    FROM user_progress up
                    JOIN exercises e ON e.id = up.exercise_id
                    WHERE up.user_id = ? AND e.level = ?
                    ORDER BY up.completed_time DESC""",
                    (user_id, level),
                )
            else:
                cursor = await self.db.execute(
                    """SELECT up.*, e.level AS exercise_level, e.title AS exercise_title
                    FROM user_progress up
                    JOIN exercises e ON e.id = up.exercise_id
                    WHERE up.user_id = ?
                    ORDER BY up.completed_time DESC""",
                    (user_id,),
                )
            rows = await cursor.fetchall()
            records = [dict(row) for row in rows]

            total_score = sum(r["score"] for r in records)
            total_questions = sum(r["total_questions"] for r in records)
            completed_exercises = len(records)
            accuracy = (
                round((total_score / total_questions) * 100, 1)
                if total_questions > 0
                else 0.0
            )

            return {
                "user_id": user_id,
                "level": level,
                "completed_exercises": completed_exercises,
                "total_score": total_score,
                "total_questions": total_questions,
                "accuracy": accuracy,
                "records": records,
            }
        except Exception as e:
            logger.error(f"Error fetching progress for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "level": level,
                "completed_exercises": 0,
                "total_score": 0,
                "total_questions": 0,
                "accuracy": 0.0,
                "records": [],
            }

    async def update_user_activity(self, user_id: int) -> None:
        await self._ensure_connected()
        try:
            today = date.today().isoformat()
            cursor = await self.db.execute(
                "SELECT last_active_date, streak_days FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                await self.db.execute(
                    "INSERT INTO users (user_id, streak_days, last_active_date) VALUES (?, 1, ?)",
                    (user_id, today),
                )
                await self.db.commit()
                return

            last_active = row["last_active_date"]
            streak = row["streak_days"] or 0
            if last_active:
                delta = (date.today() - datetime.strptime(last_active, "%Y-%m-%d").date()).days
                new_streak = streak + 1 if delta == 1 else (1 if delta > 1 else streak)
            else:
                new_streak = 1

            await self.db.execute(
                "UPDATE users SET streak_days = ?, last_active_date = ? WHERE user_id = ?",
                (new_streak, today, user_id),
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error updating activity for user {user_id}: {e}")

    async def save_user_progress(self, user_id: int, exercise_id: int, score: int, total: int) -> None:
        await self._ensure_connected()
        try:
            await self.db.execute(
                """INSERT INTO user_progress (user_id, exercise_id, score, total_questions)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, exercise_id) DO UPDATE SET
                    score = excluded.score, total_questions = excluded.total_questions,
                    completed_time = CURRENT_TIMESTAMP""",
                (user_id, exercise_id, score, total),
            )
            await self.db.commit()
            await self.update_user_activity(user_id)
        except Exception as e:
            logger.error(f"Error saving progress: {e}")