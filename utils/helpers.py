import os
import sys
import json
import logging
import random
import string
import re
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class Helpers:
    """فئة المساعدات العامة للبوت"""
    
    @staticmethod
    def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
        """
        إعداد نظام السجلات
        
        Args:
            log_level: مستوى السجل (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: مسار ملف السجل (اختياري)
            
        Returns:
            كائن السجل
        """
        # إنشاء formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # إعداد logger الأساسي
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # إضافة console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # إضافة file handler إذا تم تحديد ملف
        if log_file:
            # إنشاء مجلد السجلات إذا لم يكن موجوداً
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    @staticmethod
    def validate_telegram_link(link: str) -> bool:
        """
        التحقق من صحة رابط تليجرام
        
        Args:
            link: الرابط المراد التحقق منه
            
        Returns:
            True إذا كان الرابط صالحاً
        """
        patterns = [
            r'^https?://t\.me/[a-zA-Z0-9_]{5,}$',  # رابط عادي
            r'^https?://t\.me/\+[a-zA-Z0-9_\-]{10,}$',  # رابط دعوة
            r'^https?://t\.me/addlist/[a-zA-Z0-9_\-]+$',  # رابط قائمة
            r'^t\.me/[a-zA-Z0-9_]{5,}$',
            r'^t\.me/\+[a-zA-Z0-9_\-]{10,}$',
            r'^t\.me/addlist/[a-zA-Z0-9_\-]+$',
            r'^\+[a-zA-Z0-9_\-]{10,}$',
            r'^@[a-zA-Z0-9_]{5,}$'
        ]
        
        for pattern in patterns:
            if re.match(pattern, link):
                return True
        
        return False
    
    @staticmethod
    def extract_links_from_text(text: str) -> List[str]:
        """
        استخراج جميع روابط تليجرام من النص
        
        Args:
            text: النص المراد استخراج الروابط منه
            
        Returns:
            قائمة بالروابط المستخرجة
        """
        # نمط للبحث عن روابط تليجرام
        pattern = r'(https?://t\.me/[^\s]+|t\.me/[^\s]+|\+[a-zA-Z0-9_\-]+|@[a-zA-Z0-9_]+)'
        
        links = re.findall(pattern, text)
        
        # تصفية الروابط الصالحة فقط
        valid_links = []
        for link in links:
            if Helpers.validate_telegram_link(link):
                valid_links.append(link.strip())
        
        return valid_links
    
    @staticmethod
    def clean_filename(filename: str) -> str:
        """
        تنظيف اسم الملف من الأحغير غير الآمنة
        
        Args:
            filename: اسم الملف المراد تنظيفه
            
        Returns:
            اسم ملف نظيف
        """
        # إزالة الأحرف غير الآمنة
        cleaned = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # تقصير إذا كان طويلاً جداً
        if len(cleaned) > 100:
            name, ext = os.path.splitext(cleaned)
            cleaned = name[:95] + ext
        
        return cleaned
    
    @staticmethod
    def generate_unique_filename(original_name: str, directory: str) -> str:
        """
        إنشاء اسم ملف فريد في المجلد المحدد
        
        Args:
            original_name: اسم الملف الأصلي
            directory: المجلد المستهدف
            
        Returns:
            اسم ملف فريد
        """
        # تنظيف اسم الملف
        clean_name = Helpers.clean_filename(original_name)
        
        # إذا كان الملف غير موجود، استخدم الاسم كما هو
        file_path = os.path.join(directory, clean_name)
        if not os.path.exists(file_path):
            return clean_name
        
        # إذا كان الملف موجوداً، أضف رقم تسلسلي
        name, ext = os.path.splitext(clean_name)
        counter = 1
        
        while os.path.exists(os.path.join(directory, f"{name}_{counter}{ext}")):
            counter += 1
        
        return f"{name}_{counter}{ext}"
    
    @staticmethod
    def create_directories(directories: List[str]) -> bool:
        """
        إنشاء مجلدات متعددة
        
        Args:
            directories: قائمة بمسارات المجلدات المراد إنشاؤها
            
        Returns:
            True إذا تم إنشاء جميع المجلدات بنجاح
        """
        try:
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"✅ تم إنشاء المجلد: {directory}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء المجلدات: {str(e)}")
            return False
    
    @staticmethod
    def cleanup_old_files(directory: str, days: int = 7) -> int:
        """
        تنظيف الملفات القديمة من مجلد
        
        Args:
            directory: مسار المجلد
            days: عدد الأيام (الملفات الأقدم من هذا سيتم حذفها)
            
        Returns:
            عدد الملفات المحذوفة
        """
        if not os.path.exists(directory):
            return 0
        
        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(days=days)
        
        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.debug(f"🗑️ تم حذف الملف القديم: {filename}")
            
            if deleted_count > 0:
                logger.info(f"🧹 تم تنظيف {deleted_count} ملف قديم من {directory}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف الملفات القديمة: {str(e)}")
            return 0
    
    @staticmethod
    def format_bytes(size_bytes: int) -> str:
        """
        تنسيق حجم الملف من بايت إلى وحدات قابلة للقراءة
        
        Args:
            size_bytes: الحجم بالبايت
            
        Returns:
            حجم منسق (مثل "1.5 MB")
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.2f} {units[i]}"
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """
        الحصول على معلومات عن ملف
        
        Args:
            file_path: مسار الملف
            
        Returns:
            قاموس بمعلومات الملف
        """
        if not os.path.exists(file_path):
            return {"error": "الملف غير موجود"}
        
        try:
            stat_info = os.stat(file_path)
            
            info = {
                "filename": os.path.basename(file_path),
                "path": os.path.abspath(file_path),
                "size": stat_info.st_size,
                "size_formatted": Helpers.format_bytes(stat_info.st_size),
                "created": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                "extension": os.path.splitext(file_path)[1].lower(),
                "is_file": os.path.isfile(file_path),
                "is_dir": os.path.isdir(file_path)
            }
            
            return info
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def generate_random_string(length: int = 10) -> str:
        """
        إنشاء نص عشوائي
        
        Args:
            length: طول النص المطلوب
            
        Returns:
            نص عشوائي
        """
        characters = string.ascii_letters + string.digits
        return ''.join(random.choices(characters, k=length))
    
    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        تنسيق كائن datetime إلى نص
        
        Args:
            dt: كائن datetime
            format_str: تنسيق الناتج
            
        Returns:
            datetime منسق كنص
        """
        return dt.strftime(format_str)
    
    @staticmethod
    def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
        """
        تحويل نص إلى كائن datetime
        
        Args:
            date_str: نص التاريخ
            format_str: تنسيق النص
            
        Returns:
            كائن datetime أو None إذا فشل التحليل
        """
        try:
            return datetime.strptime(date_str, format_str)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def time_ago(dt: datetime) -> str:
        """
        الحصول على وقت مضى بصيغة بشرية
        
        Args:
            dt: وقت الماضي
            
        Returns:
            نص مثل "منذ 5 دقائق"
        """
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 365:
            years = diff.days // 365
            return f"منذ {years} سنة" if years == 1 else f"منذ {years} سنوات"
        
        elif diff.days > 30:
            months = diff.days // 30
            return f"منذ {months} شهر" if months == 1 else f"منذ {months} أشهر"
        
        elif diff.days > 0:
            return f"منذ {diff.days} يوم" if diff.days == 1 else f"منذ {diff.days} أيام"
        
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"منذ {hours} ساعة" if hours == 1 else f"منذ {hours} ساعات"
        
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"منذ {minutes} دقيقة" if minutes == 1 else f"منذ {minutes} دقائق"
        
        else:
            return "الآن"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        تقصير النص إذا كان طويلاً
        
        Args:
            text: النص الأصلي
            max_length: الطول الأقصى
            suffix: اللاحقة التي تضاف للنص المقصوص
            
        Returns:
            نص مقصوص إذا كان طويلاً
        """
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def split_text(text: str, max_length: int = 4000) -> List[str]:
        """
        تقسيم النص إلى أجزاء إذا كان طويلاً جداً
        
        Args:
            text: النص الأصلي
            max_length: الطول الأقصى لكل جزء
            
        Returns:
            قائمة بأجزاء النص
        """
        if len(text) <= max_length:
            return [text]
        
        parts = []
        while text:
            if len(text) <= max_length:
                parts.append(text)
                break
            
            # حاول القطع عند أقرب مسافة
            cut_point = text[:max_length].rfind(' ')
            if cut_point == -1:
                cut_point = max_length
            
            parts.append(text[:cut_point])
            text = text[cut_point:].strip()
        
        return parts
    
    @staticmethod
    def create_backup(file_path: str, backup_dir: str = "backups") -> Tuple[bool, str]:
        """
        إنشاء نسخة احتياطية لملف
        
        Args:
            file_path: مسار الملف الأصلي
            backup_dir: مجلد النسخ الاحتياطية
            
        Returns:
            (نجاح العملية، مسار النسخة الاحتياطية)
        """
        if not os.path.exists(file_path):
            return False, "الملف الأصلي غير موجود"
        
        try:
            # إنشاء مجلد النسخ الاحتياطية
            os.makedirs(backup_dir, exist_ok=True)
            
            # إنشاء اسم النسخة الاحتياطية
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(file_path)
            backup_name = f"{filename}.backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)
            
            # نسخ الملف
            shutil.copy2(file_path, backup_path)
            
            logger.info(f"✅ تم إنشاء نسخة احتياطية: {backup_path}")
            return True, backup_path
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء النسخة الاحتياطية: {str(e)}")
            return False, str(e)
    
    @staticmethod
    async def async_wait(seconds: float):
        """
        انتظار غير متزامن
        
        Args:
            seconds: عدد الثواني للانتظار
        """
        await asyncio.sleep(seconds)
    
    @staticmethod
    def is_valid_session_string(session_string: str) -> bool:
        """
        التحقق من صحة كود الجلسة الأساسي
        
        Args:
            session_string: كود الجلسة
            
        Returns:
            True إذا كان الكود صالحاً من حيث الطول والشكل
        """
        if not session_string or not isinstance(session_string, str):
            return False
        
        # التحقق من الطول الأدنى
        if len(session_string) < 100:
            return False
        
        # التحقق من وجود أحرف صالحة فقط
        valid_chars = string.ascii_letters + string.digits + "+/="
        for char in session_string:
            if char not in valid_chars:
                return False
        
        return True
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        الحصول على معلومات النظام
        
        Returns:
            معلومات النظام
        """
        import platform
        import psutil
        
        try:
            info = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/')._asdict(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "current_time": datetime.now().isoformat()
            }
            
            return info
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def create_vcf_file(contact_data: Dict[str, str], output_path: str) -> bool:
        """
        إنشاء ملف VCF (جهة اتصال)
        
        Args:
            contact_data: بيانات جهة الاتصال
            output_path: مسار الملف الناتج
            
        Returns:
            True إذا تم الإنشاء بنجاح
        """
        try:
            vcf_lines = []
            vcf_lines.append("BEGIN:VCARD")
            vcf_lines.append("VERSION:3.0")
            
            # الاسم الكامل
            full_name = contact_data.get('full_name', 'تسوي سكليف صحتي واتساب')
            vcf_lines.append(f"FN:{full_name}")
            
            # الاسم
            first_name = contact_data.get('first_name', 'تسوي')
            last_name = contact_data.get('last_name', 'سكليف صحتي واتساب')
            vcf_lines.append(f"N:{last_name};{first_name};;;")
            
            # رقم الهاتف
            phone = contact_data.get('phone', '')
            if phone:
                vcf_lines.append(f"TEL;TYPE=CELL:{phone}")
            
            # معرف التليجرام
            telegram_id = contact_data.get('telegram_id', '')
            if telegram_id:
                vcf_lines.append(f"X-TELEGRAM-ID:{telegram_id}")
            
            # البريد الإلكتروني
            email = contact_data.get('email', '')
            if email:
                vcf_lines.append(f"EMAIL:{email}")
            
            # الملاحظات
            notes = contact_data.get('notes', '')
            if notes:
                vcf_lines.append(f"NOTE:{notes}")
            
            vcf_lines.append("END:VCARD")
            
            # حفظ الملف
            vcf_content = "\n".join(vcf_lines)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(vcf_content)
            
            logger.info(f"✅ تم إنشاء ملف VCF: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء ملف VCF: {str(e)}")
            return False
