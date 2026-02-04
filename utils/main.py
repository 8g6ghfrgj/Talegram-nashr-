"""
نقطة دخول لاختبار أدوات المساعدة
"""
import sys
import os

# إضافة المسار الحالي إلى sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers import Helpers
from text_encoder import TextEncoder

def test_helpers():
    """اختبار أدوات المساعدة"""
    print("🧪 اختبار أدوات المساعدة...")
    
    # اختبار إنشاء نص عشوائي
    random_text = Helpers.generate_random_string(20)
    print(f"📝 نص عشوائي: {random_text}")
    
    # اختبار التحقق من رابط تليجرام
    test_links = [
        "https://t.me/testchannel",
        "t.me/test",
        "@username",
        "+invitecode",
        "invalid_link"
    ]
    
    for link in test_links:
        is_valid = Helpers.validate_telegram_link(link)
        print(f"🔗 {link}: {'✅ صالح' if is_valid else '❌ غير صالح'}")
    
    # اختبار تنسيق التاريخ
    from datetime import datetime, timedelta
    past_time = datetime.now() - timedelta(hours=2)
    time_ago_str = Helpers.time_ago(past_time)
    print(f"⏰ منذ: {time_ago_str}")
    
    print("✅ تم اختبار أدوات المساعدة بنجاح")

def test_text_encoder():
    """اختبار مشفر النصوص"""
    print("\n🔐 اختبار مشفر النصوص...")
    
    encoder = TextEncoder()
    
    # نص للاختبار
    test_text = "هذا نص سري للاختبار مع أحرف عربية وإنجليزية: Test 123"
    
    # تشفير متقدم
    encoded = encoder.encode_text(test_text, use_advanced=True)
    print(f"📤 مشفر (متقدم): {encoded[:50]}...")
    
    # فك التشفير
    decoded = encoder.decode_text(encoded)
    print(f"📥 مفكوك: {decoded}")
    
    # التحقق من التطابق
    if test_text == decoded:
        print("✅ التشفير وفك التشفير ناجح!")
    else:
        print("❌ خطأ في التشفير/فك التشفير")
    
    # اختبار الهاش
    hash_result = encoder.create_hash(test_text)
    print(f"🔢 الهاش: {hash_result}")
    
    print("✅ تم اختبار مشفر النصوص بنجاح")

def test_file_operations():
    """اختبار عمليات الملفات"""
    print("\n📁 اختبار عمليات الملفات...")
    
    # اختبار تنظيف اسم الملف
    dirty_name = 'file<>:"/\\|?*name.txt'
    clean_name = Helpers.clean_filename(dirty_name)
    print(f"🧹 تنظيف اسم الملف: {dirty_name} -> {clean_name}")
    
    # اختبار معلومات النظام
    system_info = Helpers.get_system_info()
    print(f"💻 نظام التشغيل: {system_info.get('system', 'غير معروف')}")
    
    print("✅ تم اختبار عمليات الملفات بنجاح")

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 بدء اختبار أدوات المساعدة")
    print("=" * 50)
    
    try:
        test_helpers()
        test_text_encoder()
        test_file_operations()
        
        print("\n" + "=" * 50)
        print("🎉 جميع الاختبارات نجحت!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ خطأ في الاختبار: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
