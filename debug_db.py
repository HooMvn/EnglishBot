"""
اسکریپت دیباگ دیتابیس - بررسی اینکه آیا داده‌ها قابل بازیابی هستند
"""
import sqlite3

DB_PATH = "data/database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 70)
print("🔍 دیباگ دیتابیس")
print("=" * 70)

# ۱. تعداد کل رکوردها
cursor.execute("SELECT COUNT(*) FROM audio_tracks")
print(f"\n🎵 تعداد کل ویس‌ها: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM resources")
print(f"📚 تعداد کل منابع: {cursor.fetchone()[0]}")

# ۲. بررسی سطوح موجود
print("\n📊 سطوح موجود در audio_tracks:")
cursor.execute("SELECT DISTINCT level FROM audio_tracks ORDER BY level")
for row in cursor.fetchall():
    print(f"   - '{row[0]}'")

# ۳. بررسی book_type ها
print("\n📊 انواع کتاب موجود:")
cursor.execute("SELECT DISTINCT book_type FROM audio_tracks ORDER BY book_type")
for row in cursor.fetchall():
    print(f"   - '{row[0]}'")

# ۴. تست کوئری‌های مختلف (شبیه‌سازی آنچه ربات انجام می‌دهد)
print("\n🧪 تست کوئری‌ها:")

test_queries = [
    ("starter + student_book + unit 1", 
     "SELECT COUNT(*) FROM audio_tracks WHERE level='starter' AND book_type='student_book' AND unit=1"),
    ("level_1 + student_book + unit 1", 
     "SELECT COUNT(*) FROM audio_tracks WHERE level='level_1' AND book_type='student_book' AND unit=1"),
    ("level_1 + workbook + unit 1", 
     "SELECT COUNT(*) FROM audio_tracks WHERE level='level_1' AND book_type='workbook' AND unit=1"),
    ("level_2 + student_book + unit 3", 
     "SELECT COUNT(*) FROM audio_tracks WHERE level='level_2' AND book_type='student_book' AND unit=3"),
    ("فقط level=starter", 
     "SELECT COUNT(*) FROM audio_tracks WHERE level='starter'"),
    ("فقط level=level_1", 
     "SELECT COUNT(*) FROM audio_tracks WHERE level='level_1'"),
]

for name, query in test_queries:
    cursor.execute(query)
    count = cursor.fetchone()[0]
    status = "✅" if count > 0 else "❌"
    print(f"   {status} {name}: {count} ویس")

# ۵. نمایش چند نمونه واقعی
print("\n📋 ۵ نمونه ویس از level_1, student_book, unit 1:")
cursor.execute("""
    SELECT track_number, title, audio_file_id, duration 
    FROM audio_tracks 
    WHERE level='level_1' AND book_type='student_book' AND unit=1 
    ORDER BY track_number 
    LIMIT 5
""")
for row in cursor.fetchall():
    fid = row[2][:30] + "..." if row[2] else "None"
    print(f"   Track {row[0]} | {row[1]} | Duration: {row[3]}s | FileID: {fid}")

# ۶. بررسی منابع
print("\n📋 منابع Starter:")
cursor.execute("SELECT resource_type, title, file_id FROM resources WHERE level='starter'")
for row in cursor.fetchall():
    fid = row[2][:30] + "..." if row[2] else "None"
    print(f"   {row[0]} | {row[1]} | FileID: {fid}")

# ۷. بررسی ساختار جدول
print("\n🏗️ ساختار جدول audio_tracks:")
cursor.execute("PRAGMA table_info(audio_tracks)")
for col in cursor.fetchall():
    print(f"   ستون: {col[1]} | نوع: {col[2]}")

conn.close()
print("\n" + "=" * 70)
print("✅ دیباگ تمام شد")
print("=" * 70)