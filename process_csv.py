"""
اسکریپت پردازش CSV - نسخه نهایی و ضدگلوله (اصلاح اولویت تشخیص سطح)
"""
import csv
import re

INPUT_FILE = "input.csv"
AUDIO_OUTPUT = "audio_tracks_final.csv"
VIDEO_OUTPUT = "video_tracks_final.csv"
RESOURCE_OUTPUT = "resources_final.csv"

AUDIO_PATTERN = re.compile(r"AEF3e_(Starter|Level_\d+)_(SB|WB)_(\d+)\.(\d+)\.mp3", re.IGNORECASE)

def natural_sort_key(filename):
    name = filename.lower()
    parts = re.split(r'(\d+)', name)
    return [int(p) if p.isdigit() else p for p in parts]

def parse_video_filename(filename, metadata):
    level = "unknown"
    book_type = "student_book"
    unit = 1
    track_number = "1"
    category = "main"
    
    name_lower = filename.lower()
    meta_lower = metadata.lower().replace('-', ' ').replace('_', ' ').replace('#', '')
    
    # ✅ ۱. تشخیص سطح: اولویت مطلق با الگوی Level-X (برای جلوگیری از تداخل با aef3e)
    level_match = re.search(r'level[-_](\d+)', name_lower)
    if level_match:
        level = f"level_{level_match.group(1)}"
    elif meta_lower.startswith('aefs') or 'starter' in meta_lower:
        level = "starter"
    elif meta_lower.startswith('aef1') or 'book1' in meta_lower:
        level = "level_1"
    elif meta_lower.startswith('aef2') or 'book2' in meta_lower:
        level = "level_2"
    elif meta_lower.startswith('aef3') or 'book3' in meta_lower:
        level = "level_3"
    elif meta_lower.startswith('aef4') or 'book4' in meta_lower:
        level = "level_4"
    elif meta_lower.startswith('aef5') or 'book5' in meta_lower:
        level = "level_5"
    else:
        if 'sb0' in name_lower:
            level = "starter"
        else:
            sb_match = re.search(r'sb(\d+)', name_lower)
            if sb_match:
                level = f"level_{sb_match.group(1)}"
            else:
                level_match_fallback = re.search(r'level[-_]?(\d+)', name_lower)
                if level_match_fallback:
                    level = f"level_{level_match_fallback.group(1)}"
            
    # ۲. تشخیص دسته‌بندی
    if 'interview' in meta_lower:
        category = "interview"
    elif 'practical' in meta_lower:
        category = "practical"
    elif 'review' in meta_lower or 'check' in meta_lower:
        category = "review"
    elif 'listening' in meta_lower:
        category = "listening"
    elif 'street' in meta_lower:
        category = "street"
    else:
        category = "main"

    # ۳. تشخیص یونیت و شماره ترک
    review_match = re.search(r'review.*?(\d+)[&\s]+(\d+)', name_lower)
    if review_match:
        unit = review_match.group(1)
        track_number = f"{unit}.{review_match.group(2)}"
    else:
        sb_unit_match = re.search(r'sb(\d+)_(?:review_and_check_|practical_|video_)?(\d+)', name_lower)
        if sb_unit_match:
            unit = sb_unit_match.group(1)
            track_number = f"{unit}.{sb_unit_match.group(2)}"
        else:
            track_match = re.search(r'(\d+)\.(\d+)', filename)
            if track_match:
                track_number = f"{track_match.group(1)}.{track_match.group(2)}"
                unit = track_match.group(1)
            else:
                num_match = re.search(r'_(\d+)\.', filename)
                if num_match:
                    track_number = f"1.{num_match.group(1)}"
                    unit = "1"
                else:
                    unit = "1"
                    track_number = "1"
                
    return level, book_type, int(unit) if str(unit).isdigit() else 1, str(track_number), category

def get_resource_info(filename, metadata):
    """تشخیص سطح و نوع منابع - با اولویت‌بندی صحیح برای حل مشکل اسکریپت‌ها"""
    name_lower = filename.lower()
    meta_lower = metadata.lower().replace('#', '').replace(' ', '').replace('-', '')
    
    level = "unknown"
    
    # ✅ لایه ۱: اولویت مطلق با الگوی دقیق Level-X در نام فایل (مثلاً Level-1 یا Level_1)
    # این خط باید حتماً قبل از aef1, aef2, aef3 باشد!
    level_match = re.search(r'level[-_](\d+)', name_lower)
    if level_match:
        level = f"level_{level_match.group(1)}"
        
    # لایه ۲: بررسی Starter
    elif 'starter' in name_lower or 'sb0' in name_lower or 'aefs' in name_lower:
        level = "starter"
        
    # لایه ۳: بررسی BookX (دقیق‌تر از aefX)
    elif 'book1' in name_lower:
        level = "level_1"
    elif 'book2' in name_lower:
        level = "level_2"
    elif 'book3' in name_lower:
        level = "level_3"
    elif 'book4' in name_lower:
        level = "level_4"
    elif 'book5' in name_lower:
        level = "level_5"
        
    # لایه ۴: بررسی aefX (فقط اگر Level-X و BookX نبود)
    elif 'aef1' in name_lower:
        level = "level_1"
    elif 'aef2' in name_lower:
        level = "level_2"
    elif 'aef3' in name_lower:
        level = "level_3"
    elif 'aef4' in name_lower:
        level = "level_4"
    elif 'aef5' in name_lower:
        level = "level_5"
        
    # لایه ۵: بررسی متادیتا (اگر هیچکدام در نام فایل نبود)
    else:
        if 'book1' in meta_lower or 'level1' in meta_lower or 'level 1' in meta_lower or 'aef1' in meta_lower:
            level = "level_1"
        elif 'book2' in meta_lower or 'level2' in meta_lower or 'level 2' in meta_lower or 'aef2' in meta_lower:
            level = "level_2"
        elif 'book3' in meta_lower or 'level3' in meta_lower or 'level 3' in meta_lower or 'aef3' in meta_lower:
            level = "level_3"
        elif 'book4' in meta_lower or 'level4' in meta_lower or 'level 4' in meta_lower or 'aef4' in meta_lower:
            level = "level_4"
        elif 'book5' in meta_lower or 'level5' in meta_lower or 'level 5' in meta_lower or 'aef5' in meta_lower:
            level = "level_5"
        elif 'starter' in meta_lower or 'aefs' in meta_lower:
            level = "starter"
                
    # ✅ کلیدهای هماهنگ با گروه‌بندی جدید در resources.py
    resource_type = "unknown"
    if name_lower.endswith(".pdf"):
        if "tg" in name_lower or "teacher" in name_lower:
            resource_type = "teacher_pdf"
        elif "script" in name_lower:
            resource_type = "script_pdf"
        elif "sb" in name_lower or "student" in name_lower:
            resource_type = "student_book_pdf"
        elif "wb" in name_lower or "workbook" in name_lower:
            resource_type = "workbook_pdf"
        else:
            resource_type = "other_pdf"
    elif name_lower.endswith(".zip"):
        # ✅ اولویت با script برای فایل‌های ZIP اسکریپت
        if "script" in name_lower:
            resource_type = "script_zip"
        elif "interview" in name_lower:
            resource_type = "interview_video"
        elif "practical" in name_lower:
            resource_type = "practical_video"
        elif "review" in name_lower or "check" in name_lower:
            resource_type = "review_video"
        elif "street" in name_lower or "on-the-street" in name_lower:
            resource_type = "street_video"
        elif "listening" in name_lower or "video-listening" in name_lower:
            resource_type = "listening_video"
        elif "sb" in name_lower or "student" in name_lower:
            resource_type = "student_book_audio"
        elif "wb" in name_lower or "workbook" in name_lower:
            resource_type = "workbook_audio"
        else:
            resource_type = "other_zip"
            
    return level, resource_type

audio_groups = {}
audio_metadata_order = []
video_groups = {}
video_metadata_order = []
resource_rows = []

try:
    with open(INPUT_FILE, mode='r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        for row in reader:
            if len(row) < 7:
                continue
                
            filename, file_type, file_id, duration, size_mb, metadata = [x.strip() for x in row[:6]]
            if not filename or not file_id:
                continue
                
            ext = filename.split('.')[-1].lower()
            
            if ext == 'mp3':
                match = AUDIO_PATTERN.search(filename)
                if match:
                    level_raw, book_raw, unit, track_num = match.groups()
                    level = "starter" if level_raw.lower() == "starter" else level_raw.lower()
                    book_type = "student_book" if book_raw.upper() == "SB" else "workbook"
                    
                    row_data = {
                        "book_type": book_type,
                        "level": level,
                        "unit": int(unit),
                        "track_number": f"{unit}.{track_num}",
                        "title": f"Track {unit}.{track_num}",
                        "page_reference": "",
                        "type": "audio",
                        "audio_file_id": file_id,
                        "duration": int(float(duration)) if duration else 0,
                        "category": "main",
                        "metadata": metadata
                    }
                    if metadata not in audio_groups:
                        audio_groups[metadata] = []
                        audio_metadata_order.append(metadata)
                    audio_groups[metadata].append(row_data)
                    
            elif ext == 'mp4':
                level, book_type, unit, track_number, category = parse_video_filename(filename, metadata)
                row_data = {
                    "book_type": book_type,
                    "level": level,
                    "unit": unit,
                    "track_number": track_number,
                    "title": filename.replace('.mp4', ''),
                    "page_reference": "",
                    "type": "video",
                    "video_file_id": file_id,
                    "duration": int(float(duration)) if duration else 0,
                    "category": category,
                    "metadata": metadata
                }
                if metadata not in video_groups:
                    video_groups[metadata] = []
                    video_metadata_order.append(metadata)
                video_groups[metadata].append(row_data)
                
            elif ext in ['pdf', 'zip']:
                level, resource_type = get_resource_info(filename, metadata)
                resource_rows.append({
                    "level": level,
                    "resource_type": resource_type,
                    "title": filename,
                    "file_id": file_id,
                    "size_mb": float(size_mb) if size_mb else 0.0
                })

    final_audio_rows = []
    for meta in audio_metadata_order:
        final_audio_rows.extend(sorted(audio_groups[meta], key=lambda x: natural_sort_key(x['title'])))

    final_video_rows = []
    for meta in video_metadata_order:
        final_video_rows.extend(sorted(video_groups[meta], key=lambda x: natural_sort_key(x['title'])))

    with open(AUDIO_OUTPUT, mode='w', newline='', encoding='utf-8') as outfile:
        fieldnames = ["book_type", "level", "unit", "track_number", "title", "page_reference", "type", "audio_file_id", "duration", "category"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in final_audio_rows:
            row.pop('metadata', None)
            writer.writerow(row)

    with open(VIDEO_OUTPUT, mode='w', newline='', encoding='utf-8') as outfile:
        fieldnames = ["book_type", "level", "unit", "track_number", "title", "page_reference", "type", "video_file_id", "duration", "category"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in final_video_rows:
            row.pop('metadata', None)
            writer.writerow(row)

    with open(RESOURCE_OUTPUT, mode='w', newline='', encoding='utf-8') as outfile:
        fieldnames = ["level", "resource_type", "title", "file_id", "size_mb"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(resource_rows)

    print(f"✅ پردازش با موفقیت انجام شد!")
    print(f"🎵 ویس‌ها: {len(final_audio_rows)} رکورد")
    print(f"🎬 ویدیوها: {len(final_video_rows)} رکورد")
    print(f"📚 منابع: {len(resource_rows)} رکورد")

except FileNotFoundError:
    print(f"❌ خطا: فایل '{INPUT_FILE}' پیدا نشد.")
except Exception as e:
    print(f"❌ خطای غیرمنتظره: {e}")