import os
from datetime import datetime, timedelta


TEMP_DIRS = [
    "temp_files/ads",
    "temp_files/group_replies",
    "temp_files/random_replies",
    "temp_files/logs"
]


def cleanup_temp_files(days_old=7):
    """حذف الملفات الأقدم من عدد الأيام المحدد"""

    cutoff_time = datetime.now() - timedelta(days=days_old)

    print(f"🧹 تنظيف الملفات الأقدم من {days_old} أيام...\n")

    for directory in TEMP_DIRS:
        if not os.path.exists(directory):
            continue

        print(f"📂 {directory}")

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)

            if not os.path.isfile(file_path):
                continue

            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))

                if file_time < cutoff_time:
                    os.remove(file_path)
                    print(f"   🗑️ حذف: {filename}")

            except Exception as e:
                print(f"   ❌ فشل حذف {filename}: {e}")

    print("\n✅ انتهى التنظيف")


if __name__ == "__main__":
    cleanup_temp_files(7)
