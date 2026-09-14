"""
اسکریپت وارد کردن داده‌های CSV به دیتابیس اصلی ربات EnglishBot
سازگار با خروجی‌های process_csv.py (نسخه نهایی با ستون category)
"""
import csv
import sqlite3
from pathlib import Path

DB_PATH = Path(r"F:\EnglishBot\data\database.db")
AUDIO_CSV = Path(r"F:\extractbot\audio_tracks_final.csv")
VIDEO_CSV = Path(r"F:\extractbot\video_tracks_final.csv")
RESOURCE_CSV = Path(r"F:\extractbot\resources_final.csv")


def ensure_tables_and_columns(conn):
    """ایجاد جداول و اطمینان از وجود ستون category"""
    cursor = conn.cursor()
    
    cursor.execute("""
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
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE audio_tracks ADD COLUMN category TEXT DEFAULT 'main'")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE video_tracks ADD COLUMN category TEXT DEFAULT 'main'")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    print("✅ جداول و ستون‌های category بررسی/ایجاد شدند.")


def clean_old_data(conn):
    """پاک کردن تمام داده‌های قبلی"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audio_tracks")
    cursor.execute("DELETE FROM video_tracks")
    cursor.execute("DELETE FROM resources")
    conn.commit()
    print("🗑 داده‌های قبلی پاک شدند.")


def import_audio_tracks(conn):
    if not AUDIO_CSV.exists():
        print(f"️ فایل {AUDIO_CSV.name} پیدا نشد.")
        return 0
    
    cursor = conn.cursor()
    count = 0
    errors = 0
    
    with open(AUDIO_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cursor.execute("""
                    INSERT INTO audio_tracks 
                    (book_type, level, unit, track_number, title, page_reference, type, audio_file_id, duration, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['book_type'],
                    row['level'],
                    int(row['unit']),
                    row['track_number'],
                    row['title'],
                    row.get('page_reference', ''),
                    row.get('type', 'audio'),
                    row['audio_file_id'],
                    int(float(row['duration']) if row['duration'] else 0),
                    row.get('category', 'main')
                ))
                count += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"⚠️ خطا در وارد کردن {row.get('title', 'نامشخص')}: {e}")
    
    conn.commit()
    if errors > 3:
        print(f"   ... و {errors - 3} خطای دیگر")
    return count


def import_video_tracks(conn):
    if not VIDEO_CSV.exists():
        print(f"⏭️ فایل {VIDEO_CSV.name} پیدا نشد.")
        return 0
    
    cursor = conn.cursor()
    count = 0
    errors = 0
    
    with open(VIDEO_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cursor.execute("""
                    INSERT INTO video_tracks 
                    (book_type, level, unit, track_number, title, page_reference, type, video_file_id, duration, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['book_type'],
                    row['level'],
                    int(row['unit']),
                    row['track_number'],
                    row['title'],
                    row.get('page_reference', ''),
                    row.get('type', 'video'),
                    row['video_file_id'],
                    int(float(row['duration']) if row['duration'] else 0),
                    row.get('category', 'main')
                ))
                count += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"⚠️ خطا در وارد کردن {row.get('title', 'نامشخص')}: {e}")
    
    conn.commit()
    if errors > 3:
        print(f"   ... و {errors - 3} خطای دیگر")
    return count


def import_resources(conn):
    if not RESOURCE_CSV.exists():
        print(f"⏭️ فایل {RESOURCE_CSV.name} پیدا نشد.")
        return 0
    
    cursor = conn.cursor()
    count = 0
    errors = 0
    
    with open(RESOURCE_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cursor.execute("""
                    INSERT INTO resources 
                    (level, resource_type, title, file_id, size_mb)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    row['level'],
                    row['resource_type'],
                    row['title'],
                    row['file_id'],
                    float(row['size_mb']) if row['size_mb'] else 0.0
                ))
                count += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"⚠️ خطا در وارد کردن {row.get('title', 'نامشخص')}: {e}")
    
    conn.commit()
    if errors > 3:
        print(f"   ... و {errors - 3} خطای دیگر")
    return count


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 شروع وارد کردن داده‌ها به دیتابیس")
    print("=" * 70)
    
    if not DB_PATH.exists():
        print(f"❌ دیتابیس در {DB_PATH} پیدا نشد!")
        exit(1)
    
    print(f"\n📁 دیتابیس: {DB_PATH}")
    print(f"📁 فایل ویس‌ها: {AUDIO_CSV}")
    print(f"📁 فایل ویدیوها: {VIDEO_CSV}")
    print(f"📁 فایل منابع: {RESOURCE_CSV}\n")
    print("-" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    ensure_tables_and_columns(conn)
    clean_old_data(conn)
    print("-" * 70)
    
    print(" وارد کردن ویس‌ها...")
    audio_count = import_audio_tracks(conn)
    print(f"✅ {audio_count} ویس وارد شد.\n")
    
    print("🎬 وارد کردن ویدیوها...")
    video_count = import_video_tracks(conn)
    print(f"✅ {video_count} ویدیو وارد شد.\n")
    
    print("📚 وارد کردن منابع...")
    resource_count = import_resources(conn)
    print(f"✅ {resource_count} منبع وارد شد.\n")
    
    total = audio_count + video_count + resource_count
    print("=" * 70)
    print(f"🎉 کار تمام شد! مجموعاً {total} رکورد وارد دیتابیس شد.")
    print(f"    🎵 ویس‌ها: {audio_count}")
    print(f"    🎬 ویدیوها: {video_count}")
    print(f"    📚 منابع: {resource_count}")
    print("=" * 70)
    
    conn.close()