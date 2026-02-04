import asyncio
import threading
import os
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

try:
    from telethon import TelegramClient, errors
    from telethon.sessions import StringSession
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.functions.messages import ImportChatInviteRequest
    from telethon.tl.types import InputPeerEmpty
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    logging.error("Telethon not installed. Please install it with: pip install telethon")

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
    logging.error("SQLite3 not available. This is built-in in Python.")

from config import DELAY_SETTINGS, OWNER_ID

logger = logging.getLogger(__name__)

class TelegramBotManager:
    def __init__(self, db):
        if not TELETHON_AVAILABLE:
            raise ImportError("Telethon library is required. Install with: pip install telethon")
        if not SQLITE_AVAILABLE:
            raise ImportError("SQLite3 is not available. This should be built-in in Python.")
        
        self.db = db
        
        # إعدادات التأخير مع القيم الافتراضية
        self.delay_settings = DELAY_SETTINGS or {
            'publishing': {'between_ads': 0.1, 'between_groups': 0.2, 'between_cycles': 30, 'group_publishing_delay': 60},
            'private_reply': {'between_replies': 0.05, 'between_cycles': 3},
            'group_reply': {'between_replies': 0.05, 'between_cycles': 3},
            'random_reply': {'between_replies': 0.05, 'between_cycles': 3},
            'join_groups': {'between_links': 90, 'between_cycles': 5}
        }
        
        # حالات المهام
        self.publishing_active = {}
        self.publishing_tasks = {}
        self.private_reply_active = {}
        self.private_reply_tasks = {}
        self.group_reply_active = {}
        self.group_reply_tasks = {}
        self.random_reply_active = {}
        self.random_reply_tasks = {}
        self.join_groups_active = {}
        self.join_groups_tasks = {}
        
        # ذاكرة التخزين المؤقت للعملاء
        self.client_cache = {}
        
        # قفل للتزامن
        self.lock = threading.Lock()
        
        # إحصائيات
        self.stats = {
            'publish_count': 0,
            'reply_count': 0,
            'join_count': 0,
            'errors': 0,
            'last_activity': datetime.now()
        }
        
        # جلسات API (يجب استبدالها بقيمك الفعلية)
        self.api_id = 1  # TODO: استبدل بـ API ID الحقيقي من my.telegram.org
        self.api_hash = "b"  # TODO: استبدل بـ API Hash الحقيقي من my.telegram.org
        
        logger.info("✅ تم تهيئة مدير تليجرام")
        logger.info(f"⚙️ إعدادات التأخير: نشر القروبات كل {self.delay_settings['publishing']['group_publishing_delay']} ثانية")
    
    async def get_client(self, session_string: str) -> Optional[TelegramClient]:
        """الحصول على عميل من الذاكرة المؤقتة مع معالجة الأخطاء"""
        if session_string not in self.client_cache:
            try:
                # التحقق من صحة session string
                if not session_string or len(session_string) < 100:
                    logger.error(f"❌ session string غير صالح (قصير جداً)")
                    return None
                
                # إنشاء عميل جديد
                client = TelegramClient(
                    StringSession(session_string),
                    api_id=self.api_id,
                    api_hash=self.api_hash
                )
                
                await client.connect()
                
                # التحقق من تفعيل الجلسة
                if await client.is_user_authorized():
                    self.client_cache[session_string] = client
                    logger.debug(f"✅ تم توصيل العميل للجلسة: {session_string[:20]}...")
                else:
                    await client.disconnect()
                    logger.error(f"❌ جلسة غير مفعلة: {session_string[:20]}...")
                    return None
                    
            except errors.rpcerrorlist.AuthKeyDuplicatedError:
                logger.error(f"❌ مفتاح المصادقة مكرر (الحساب مستخدم على جهاز آخر)")
                return None
            except errors.rpcerrorlist.AuthKeyInvalidError:
                logger.error(f"❌ مفتاح مصادقة غير صالح (جلسة منتهية)")
                return None
            except errors.rpcerrorlist.SessionPasswordNeededError:
                logger.error(f"❌ الجلسة تحتاج كلمة مرور")
                return None
            except errors.FloodWaitError as e:
                logger.warning(f"⏳ Flood wait: {e.seconds} ثانية")
                await asyncio.sleep(e.seconds + 1)
                return await self.get_client(session_string)  # إعادة المحاولة
            except Exception as e:
                logger.error(f"❌ خطأ في الاتصال بالجلسة: {type(e).__name__}: {str(e)}")
                return None
        
        return self.client_cache.get(session_string)
    
    async def cleanup_client(self, session_string: str):
        """تنظيف العميل من الذاكرة المؤقتة"""
        if session_string in self.client_cache:
            try:
                client = self.client_cache[session_string]
                await client.disconnect()
                logger.debug(f"✅ تم فصل العميل للجلسة: {session_string[:20]}...")
            except Exception as e:
                logger.error(f"❌ خطأ في فصل العميل: {str(e)}")
            finally:
                del self.client_cache[session_string]
    
    async def cleanup_all(self):
        """تنظيف جميع العملاء"""
        logger.info("🧹 جاري تنظيف جميع العملاء...")
        cleanup_tasks = []
        for session_string in list(self.client_cache.keys()):
            cleanup_tasks.append(self.cleanup_client(session_string))
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        logger.info("✅ تم تنظيف جميع العملاء")
    
    async def test_session(self, session_string: str) -> Tuple[bool, str]:
        """اختبار جلسة وحساب معلوماته"""
        try:
            client = await self.get_client(session_string)
            if not client:
                return False, "❌ فشل في الاتصال بالجلسة"
            
            if await client.is_user_authorized():
                me = await client.get_me()
                await self.cleanup_client(session_string)
                
                info = {
                    'id': me.id,
                    'first_name': me.first_name or '',
                    'last_name': me.last_name or '',
                    'username': f"@{me.username}" if me.username else "لا يوجد",
                    'phone': me.phone or "غير معروف"
                }
                
                return True, f"✅ الحساب صالح: {info['first_name']} {info['last_name']} ({info['phone']})"
            else:
                await client.disconnect()
                return False, "❌ الجلسة غير مفعلة"
                
        except Exception as e:
            return False, f"❌ خطأ في اختبار الجلسة: {str(e)}"
    
    # ============ مهام النشر ============
    
    async def publish_to_groups_task(self, admin_id: int):
        """مهمة النشر في المجموعات مع تأخير 60 ثانية بين نشر القروبات"""
        logger.info(f"🚀 بدأ النشر للمشرف {admin_id}")
        
        while self.publishing_active.get(admin_id, False):
            try:
                # تحديث وقت النشاط
                self.stats['last_activity'] = datetime.now()
                
                # الحصول على الحسابات النشطة
                accounts = self.db.get_active_publishing_accounts(admin_id)
                
                # الحصول على الإعلانات
                ads = self.db.get_ads(admin_id)
                
                if not accounts or not ads:
                    logger.info(f"⏳ انتظار للحسابات/إعلانات للمشرف {admin_id}")
                    await asyncio.sleep(self.delay_settings['publishing']['between_cycles'])
                    continue
                
                logger.info(f"📊 النشر للمشرف {admin_id}: {len(accounts)} حساب، {len(ads)} إعلان")
                
                # النشر من كل حساب
                for account in accounts:
                    if not self.publishing_active.get(admin_id, False):
                        break
                    
                    account_id, session_string, name, username = account
                    
                    try:
                        # الحصول على العميل
                        client = await self.get_client(session_string)
                        if not client:
                            logger.error(f"❌ فشل الحصول على العميل للحساب {name}")
                            continue
                        
                        # الحصول على المجموعات
                        try:
                            dialogs = await client.get_dialogs(limit=50)  # تقليل الحد لتجنب الضغط
                        except errors.FloodWaitError as e:
                            logger.warning(f"⏳ Flood wait في جلب الدردشات: {e.seconds} ثانية")
                            await asyncio.sleep(e.seconds + 1)
                            continue
                        except Exception as e:
                            logger.error(f"❌ خطأ في جلب الدردشات للحساب {name}: {str(e)}")
                            await self.cleanup_client(session_string)
                            continue
                        
                        # تصفية المجموعات والقنوات فقط
                        groups_channels = [d for d in dialogs if d.is_group or d.is_channel]
                        
                        if not groups_channels:
                            logger.info(f"ℹ️ لا توجد مجموعات/قنوات للحساب {name}")
                            continue
                        
                        logger.info(f"📨 جاهز للنشر في {len(groups_channels)} مجموعة/قناة بواسطة {name}")
                        
                        # نشر في كل مجموعة
                        for dialog in groups_channels:
                            if not self.publishing_active.get(admin_id, False):
                                break
                            
                            try:
                                logger.debug(f"📝 نشر في {dialog.name or 'غير معروف'} بواسطة {name}")
                                
                                # نشر جميع الإعلانات
                                for ad in ads:
                                    if not self.publishing_active.get(admin_id, False):
                                        break
                                    
                                    ad_id, ad_type, ad_text, media_path, file_type, added_date, ad_admin_id, is_encoded = ad
                                    
                                    try:
                                        # التحقق من وجود الملف إذا كان مطلوباً
                                        if ad_type in ['photo', 'contact'] and media_path:
                                            if not os.path.exists(media_path):
                                                logger.error(f"❌ الملف غير موجود: {media_path}")
                                                continue
                                        
                                        # النشر حسب نوع الإعلان
                                        if ad_type == 'text':
                                            await client.send_message(dialog.id, ad_text)
                                            logger.info(f"✅ نشر نص في {dialog.name} بواسطة {name}")
                                            
                                        elif ad_type == 'photo' and media_path:
                                            await client.send_file(dialog.id, media_path, caption=ad_text)
                                            logger.info(f"✅ نشر صورة في {dialog.name} بواسطة {name}")
                                            
                                        elif ad_type == 'contact' and media_path:
                                            if media_path.endswith('.vcf'):
                                                with open(media_path, 'rb') as f:
                                                    await client.send_file(
                                                        dialog.id, 
                                                        f, 
                                                        caption=ad_text,
                                                        file_name="تسوي سكليف صحتي واتساب.vcf"
                                                    )
                                                logger.info(f"✅ نشر جهة اتصال في {dialog.name} بواسطة {name}")
                                        
                                        # تحديث الإحصائيات
                                        self.stats['publish_count'] += 1
                                        self.db.update_account_activity(account_id)
                                        
                                        # تأخير بين الإعلانات في نفس المجموعة
                                        await asyncio.sleep(self.delay_settings['publishing']['between_ads'])
                                        
                                    except errors.FloodWaitError as e:
                                        logger.warning(f"⏳ Flood wait في النشر: {e.seconds} ثانية")
                                        await asyncio.sleep(e.seconds + 1)
                                        continue
                                        
                                    except errors.ChatWriteForbiddenError:
                                        logger.warning(f"⚠️ لا يمكن الكتابة في {dialog.name} (محظور)")
                                        break
                                        
                                    except errors.ChannelPrivateError:
                                        logger.warning(f"🔒 قناة خاصة: {dialog.name}")
                                        break
                                        
                                    except errors.ChatAdminRequiredError:
                                        logger.warning(f"👑 يحتاج مشرف في {dialog.name}")
                                        continue
                                        
                                    except Exception as e:
                                        logger.error(f"❌ فشل نشر الإعلان {ad_id}: {type(e).__name__}: {str(e)}")
                                        self.stats['errors'] += 1
                                        continue
                                
                                # 🔴 **تأخير 60 ثانية بين نشر القروبات** 🔴
                                logger.info(f"⏱️ تأخير {self.delay_settings['publishing']['group_publishing_delay']} ثانية قبل المجموعة التالية")
                                await asyncio.sleep(self.delay_settings['publishing']['group_publishing_delay'])
                                
                            except Exception as e:
                                logger.error(f"❌ فشل النشر في {dialog.name}: {type(e).__name__}: {str(e)}")
                                continue
                        
                        # تأخير بين المجموعات المختلفة
                        await asyncio.sleep(self.delay_settings['publishing']['between_groups'])
                        
                    except Exception as e:
                        logger.error(f"❌ خطأ في الحساب {name}: {type(e).__name__}: {str(e)}")
                        await self.cleanup_client(session_string)
                        continue
                
                # تأخير بين الدورات
                logger.info(f"⏳ انتظار {self.delay_settings['publishing']['between_cycles']} ثانية للدورة القادمة")
                await asyncio.sleep(self.delay_settings['publishing']['between_cycles'])
                
            except asyncio.CancelledError:
                logger.info(f"⏹️ تم إلغاء النشر للمشرف {admin_id}")
                break
            except Exception as e:
                logger.error(f"❌ خطأ في عملية النشر: {type(e).__name__}: {str(e)}")
                await asyncio.sleep(10)
        
        logger.info(f"⏹️ توقف النشر للمشرف {admin_id}")
    
    # ============ مهام الردود ============
    
    async def handle_private_messages_task(self, admin_id: int):
        """مهمة الرد على الرسائل الخاصة"""
        logger.info(f"💬 بدأ الرد في الخاص للمشرف {admin_id}")
        
        while self.private_reply_active.get(admin_id, False):
            try:
                # تحديث وقت النشاط
                self.stats['last_activity'] = datetime.now()
                
                accounts = self.db.get_active_publishing_accounts(admin_id)
                private_replies = self.db.get_private_replies(admin_id)
                
                if not accounts or not private_replies:
                    await asyncio.sleep(self.delay_settings['private_reply']['between_cycles'])
                    continue
                
                for account in accounts:
                    if not self.private_reply_active.get(admin_id, False):
                        break
                    
                    account_id, session_string, name, username = account
                    
                    try:
                        client = await self.get_client(session_string)
                        if not client:
                            continue
                        
                        # الحصول على الرسائل الجديدة
                        try:
                            messages = await client.get_messages(None, limit=10)
                        except Exception as e:
                            logger.error(f"❌ خطأ في جلب الرسائل: {str(e)}")
                            continue
                        
                        for message in messages:
                            if not self.private_reply_active.get(admin_id, False):
                                break
                            
                            if message and hasattr(message, 'is_private') and message.is_private and not message.out:
                                for reply in private_replies:
                                    reply_id, reply_text, is_active, added_date, reply_admin_id, is_encoded = reply
                                    
                                    if is_active:
                                        try:
                                            await client.send_message(message.sender_id, reply_text)
                                            logger.info(f"💬 رد على رسالة خاصة بواسطة {name}")
                                            
                                            self.stats['reply_count'] += 1
                                            self.db.update_account_activity(account_id)
                                            
                                            # تأخير بين الردود
                                            await asyncio.sleep(self.delay_settings['private_reply']['between_replies'])
                                            break
                                            
                                        except errors.FloodWaitError as e:
                                            logger.warning(f"⏳ Flood wait في الرد الخاص: {e.seconds} ثانية")
                                            await asyncio.sleep(e.seconds + 1)
                                            continue
                                        except Exception as e:
                                            logger.error(f"❌ فشل الرد في الخاص: {str(e)}")
                                            continue
                        
                    except Exception as e:
                        logger.error(f"❌ خطأ في الحساب {name}: {str(e)}")
                        await self.cleanup_client(session_string)
                        continue
                
                await asyncio.sleep(self.delay_settings['private_reply']['between_cycles'])
                
            except asyncio.CancelledError:
                logger.info(f"⏹️ تم إلغاء الرد الخاص للمشرف {admin_id}")
                break
            except Exception as e:
                logger.error(f"❌ خطأ في معالجة الرسائل الخاصة: {str(e)}")
                await asyncio.sleep(5)
        
        logger.info(f"⏹️ توقف الرد في الخاص للمشرف {admin_id}")
    
    async def handle_group_replies_task(self, admin_id: int):
        """مهمة الردود في المجموعات"""
        logger.info(f"👥 بدأ الرد في القروبات للمشرف {admin_id}")
        
        while self.group_reply_active.get(admin_id, False):
            try:
                # تحديث وقت النشاط
                self.stats['last_activity'] = datetime.now()
                
                accounts = self.db.get_active_publishing_accounts(admin_id)
                text_replies = self.db.get_group_text_replies(admin_id)
                photo_replies = self.db.get_group_photo_replies(admin_id)
                
                if not accounts or (not text_replies and not photo_replies):
                    await asyncio.sleep(self.delay_settings['group_reply']['between_cycles'])
                    continue
                
                for account in accounts:
                    if not self.group_reply_active.get(admin_id, False):
                        break
                    
                    account_id, session_string, name, username = account
                    
                    try:
                        client = await self.get_client(session_string)
                        if not client:
                            continue
                        
                        dialogs = await client.get_dialogs(limit=30)
                        
                        for dialog in dialogs:
                            if not self.group_reply_active.get(admin_id, False):
                                break
                            
                            if dialog.is_group:
                                try:
                                    messages = await client.get_messages(dialog.id, limit=3)
                                    
                                    for message in messages:
                                        if not self.group_reply_active.get(admin_id, False):
                                            break
                                        
                                        if message and message.text and not message.out:
                                            # الردود النصية
                                            for reply in text_replies:
                                                reply_id, trigger, reply_text, is_active, added_date, reply_admin_id, is_encoded = reply
                                                
                                                if is_active and trigger.lower() in message.text.lower():
                                                    try:
                                                        await client.send_message(dialog.id, reply_text, reply_to=message.id)
                                                        logger.info(f"💬 رد على {trigger} في {dialog.name} بواسطة {name}")
                                                        
                                                        self.stats['reply_count'] += 1
                                                        self.db.update_account_activity(account_id)
                                                        
                                                        await asyncio.sleep(self.delay_settings['group_reply']['between_replies'])
                                                        break
                                                        
                                                    except errors.FloodWaitError as e:
                                                        logger.warning(f"⏳ Flood wait في الرد الجماعي: {e.seconds} ثانية")
                                                        await asyncio.sleep(e.seconds + 1)
                                                        continue
                                                    except Exception as e:
                                                        logger.error(f"❌ فشل الرد الجماعي: {str(e)}")
                                                        continue
                                            
                                            # الردود مع الصور
                                            for reply in photo_replies:
                                                reply_id, trigger, reply_text, media_path, is_active, added_date, reply_admin_id, is_encoded = reply
                                                
                                                if is_active and trigger.lower() in message.text.lower() and os.path.exists(media_path):
                                                    try:
                                                        await client.send_file(dialog.id, media_path, caption=reply_text, reply_to=message.id)
                                                        logger.info(f"🖼️ رد بصورة على {trigger} في {dialog.name} بواسطة {name}")
                                                        
                                                        self.stats['reply_count'] += 1
                                                        self.db.update_account_activity(account_id)
                                                        
                                                        await asyncio.sleep(self.delay_settings['group_reply']['between_replies'])
                                                        break
                                                        
                                                    except errors.FloodWaitError as e:
                                                        logger.warning(f"⏳ Flood wait في الرد بالصورة: {e.seconds} ثانية")
                                                        await asyncio.sleep(e.seconds + 1)
                                                        continue
                                                    except Exception as e:
                                                        logger.error(f"❌ فشل الرد بالصورة: {str(e)}")
                                                        continue
                                        
                                except Exception as e:
                                    logger.error(f"❌ فشل في المجموعة {dialog.name}: {str(e)}")
                                    continue
                        
                    except Exception as e:
                        logger.error(f"❌ خطأ في الحساب {name}: {str(e)}")
                        await self.cleanup_client(session_string)
                        continue
                
                await asyncio.sleep(self.delay_settings['group_reply']['between_cycles'])
                
            except asyncio.CancelledError:
                logger.info(f"⏹️ تم إلغاء الرد الجماعي للمشرف {admin_id}")
                break
            except Exception as e:
                logger.error(f"❌ خطأ في معالجة الردود الجماعية: {str(e)}")
                await asyncio.sleep(5)
        
        logger.info(f"⏹️ توقف الرد في القروبات للمشرف {admin_id}")
    
    async def handle_random_replies_task(self, admin_id: int):
        """مهمة الردود العشوائية في القروبات"""
        logger.info(f"🎲 بدأ الرد العشوائي للمشرف {admin_id}")
        
        while self.random_reply_active.get(admin_id, False):
            try:
                # تحديث وقت النشاط
                self.stats['last_activity'] = datetime.now()
                
                accounts = self.db.get_active_publishing_accounts(admin_id)
                random_replies = self.db.get_group_random_replies(admin_id)
                
                if not accounts or not random_replies:
                    await asyncio.sleep(self.delay_settings['random_reply']['between_cycles'])
                    continue
                
                for account in accounts:
                    if not self.random_reply_active.get(admin_id, False):
                        break
                    
                    account_id, session_string, name, username = account
                    
                    try:
                        client = await self.get_client(session_string)
                        if not client:
                            continue
                        
                        dialogs = await client.get_dialogs(limit=20)
                        
                        for dialog in dialogs:
                            if not self.random_reply_active.get(admin_id, False):
                                break
                            
                            if dialog.is_group:
                                try:
                                    messages = await client.get_messages(dialog.id, limit=2)
                                    
                                    for message in messages:
                                        if not self.random_reply_active.get(admin_id, False):
                                            break
                                        
                                        if message and message.text and not message.out and random.random() < 1.0:
                                            random_reply = random.choice(random_replies)
                                            reply_id, reply_text, media_path, is_active, added_date, reply_admin_id, is_encoded, has_media = random_reply
                                            
                                            if is_active:
                                                try:
                                                    if has_media and media_path and os.path.exists(media_path):
                                                        await client.send_file(dialog.id, media_path, caption=reply_text, reply_to=message.id)
                                                        logger.info(f"🎲 رد عشوائي مع صورة في {dialog.name} بواسطة {name}")
                                                    else:
                                                        await client.send_message(dialog.id, reply_text, reply_to=message.id)
                                                        logger.info(f"🎲 رد عشوائي في {dialog.name} بواسطة {name}")
                                                    
                                                    self.stats['reply_count'] += 1
                                                    self.db.update_account_activity(account_id)
                                                    
                                                    await asyncio.sleep(self.delay_settings['random_reply']['between_replies'])
                                                    break
                                                    
                                                except errors.FloodWaitError as e:
                                                    logger.warning(f"⏳ Flood wait في الرد العشوائي: {e.seconds} ثانية")
                                                    await asyncio.sleep(e.seconds + 1)
                                                    continue
                                                except Exception as e:
                                                    logger.error(f"❌ فشل الرد العشوائي: {str(e)}")
                                                    continue
                                        
                                except Exception as e:
                                    logger.error(f"❌ فشل في المجموعة {dialog.name}: {str(e)}")
                                    continue
                        
                    except Exception as e:
                        logger.error(f"❌ خطأ في الحساب {name}: {str(e)}")
                        await self.cleanup_client(session_string)
                        continue
                
                await asyncio.sleep(self.delay_settings['random_reply']['between_cycles'])
                
            except asyncio.CancelledError:
                logger.info(f"⏹️ تم إلغاء الرد العشوائي للمشرف {admin_id}")
                break
            except Exception as e:
                logger.error(f"❌ خطأ في معالجة الردود العشوائية: {str(e)}")
                await asyncio.sleep(5)
        
        logger.info(f"⏹️ توقف الرد العشوائي للمشرف {admin_id}")
    
    # ============ مهام الانضمام للمجموعات ============
    
    async def join_groups_task(self, admin_id: int):
        """مهمة الانضمام إلى المجموعات"""
        logger.info(f"👥 بدأ الانضمام للمجموعات للمشرف {admin_id}")
        
        while self.join_groups_active.get(admin_id, False):
            try:
                # تحديث وقت النشاط
                self.stats['last_activity'] = datetime.now()
                
                accounts = self.db.get_active_publishing_accounts(admin_id)
                groups = self.db.get_groups(admin_id, status='pending')
                
                if not accounts or not groups:
                    logger.info(f"⏳ انتظار للمجموعات/حسابات للمشرف {admin_id}")
                    await asyncio.sleep(self.delay_settings['join_groups']['between_cycles'])
                    continue
                
                logger.info(f"📊 الانضمام للمشرف {admin_id}: {len(accounts)} حساب، {len(groups)} مجموعة معلقة")
                
                for account in accounts:
                    if not self.join_groups_active.get(admin_id, False):
                        break
                    
                    account_id, session_string, name, username = account
                    
                    # الحصول على العميل مرة واحدة لكل حساب
                    client = await self.get_client(session_string)
                    if not client:
                        continue
                    
                    for group in groups[:5]:  # الحد إلى 5 مجموعات لكل دورة
                        if not self.join_groups_active.get(admin_id, False):
                            break
                        
                        group_id, link, status, join_date, added_date, group_admin_id, last_checked = group
                        
                        try:
                            success = await self.join_single_group(client, link)
                            
                            if success:
                                self.db.update_group_status(group_id, 'joined')
                                logger.info(f"✅ انضم الحساب {name} إلى المجموعة {link}")
                                
                                self.stats['join_count'] += 1
                                self.db.update_account_activity(account_id)
                            else:
                                self.db.update_group_status(group_id, 'failed')
                                logger.warning(f"❌ فشل انضمام {name} إلى {link}")
                            
                            # تأخير 90 ثانية بين الروابط
                            logger.info(f"⏱️ تأخير {self.delay_settings['join_groups']['between_links']} ثانية للرابط التالي")
                            await asyncio.sleep(self.delay_settings['join_groups']['between_links'])
                            
                        except Exception as e:
                            logger.error(f"❌ خطأ في المجموعة {link}: {str(e)}")
                            continue
                    
                    # تنظيف العميل بعد الانتهاء
                    await self.cleanup_client(session_string)
                
                await asyncio.sleep(self.delay_settings['join_groups']['between_cycles'])
                
            except asyncio.CancelledError:
                logger.info(f"⏹️ تم إلغاء الانضمام للمشرف {admin_id}")
                break
            except Exception as e:
                logger.error(f"❌ خطأ في عملية الانضمام: {str(e)}")
                await asyncio.sleep(5)
        
        logger.info(f"⏹️ توقف الانضمام للمجموعات للمشرف {admin_id}")
    
    async def join_single_group(self, client: TelegramClient, group_link: str) -> bool:
        """الانضمام إلى مجموعة واحدة"""
        try:
            logger.debug(f"🔗 محاولة الانضمام إلى: {group_link}")
            
            # تنظيف الرابط
            original_link = group_link
            if group_link.startswith('https://'):
                group_link = group_link.replace('https://', '')
            
            if group_link.startswith('t.me/'):
                group_link = group_link.replace('t.me/', '')
            
            # التعامل مع أنواع الروابط المختلفة
            if group_link.startswith('+') or 'joinchat' in group_link:
                # رابط دعوة
                if group_link.startswith('+'):
                    invite_hash = group_link[1:]
                else:
                    invite_hash = group_link.split('/')[-1]
                
                await client(ImportChatInviteRequest(invite_hash))
                logger.info(f"✅ انضم عبر رابط دعوة: {original_link}")
                return True
            
            elif 'addlist' in group_link:
                # رابط قائمة (مجلد)
                folder_hash = group_link.split('/')[-1]
                try:
                    await client(ImportChatInviteRequest(folder_hash))
                    logger.info(f"✅ انضم عبر رابط قائمة: {original_link}")
                    return True
                except errors.InviteHashExpiredError:
                    logger.info(f"⏰ رابط مجلد منتهي: {original_link}")
                    return False
                except:
                    try:
                        await client(JoinChannelRequest(f'@{folder_hash}'))
                        logger.info(f"✅ انضم عبر رابط مجلد: {original_link}")
                        return True
                    except Exception as e:
                        logger.error(f"❌ فشل في رابط المجلد: {original_link} - {str(e)}")
                        return False
            else:
                # رابط عادي
                try:
                    # إزالة @ إذا كانت موجودة
                    if group_link.startswith('@'):
                        group_link = group_link[1:]
                    
                    await client(JoinChannelRequest(f'@{group_link}'))
                    logger.info(f"✅ انضم عبر رابط عادي: {original_link}")
                    return True
                except errors.ChannelInvalidError:
                    logger.error(f"❌ رابط غير صالح: {original_link}")
                    return False
                
        except errors.FloodWaitError as e:
            logger.warning(f"⏳ Flood wait: {e.seconds} ثانية للرابط {original_link}")
            await asyncio.sleep(e.seconds + 1)
            return False  # لا تحاول مرة أخرى في هذه الدورة
            
        except errors.ChannelPrivateError:
            logger.error(f"🔒 القناة خاصة: {original_link}")
            return False
            
        except errors.InviteHashExpiredError:
            logger.info(f"⏰ رابط منتهي: {original_link}")
            return False
            
        except errors.InviteHashInvalidError:
            logger.error(f"❌ رابط غير صالح: {original_link}")
            return False
            
        except errors.UserAlreadyParticipantError:
            logger.info(f"✅ مستخدم بالفعل في المجموعة: {original_link}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في الانضمام إلى {original_link}: {type(e).__name__}: {str(e)}")
            return False
    
    # ============ واجهات التحكم ============
    
    def start_publishing(self, admin_id: int) -> bool:
        """بدء النشر التلقائي"""
        with self.lock:
            if not self.publishing_active.get(admin_id, False):
                self.publishing_active[admin_id] = True
                task = asyncio.create_task(self.publish_to_groups_task(admin_id))
                self.publishing_tasks[admin_id] = task
                logger.info(f"✅ بدأ النشر للمشرف {admin_id}")
                return True
            return False
    
    def stop_publishing(self, admin_id: int) -> bool:
        """إيقاف النشر التلقائي"""
        with self.lock:
            if self.publishing_active.get(admin_id, False):
                self.publishing_active[admin_id] = False
                if admin_id in self.publishing_tasks:
                    try:
                        self.publishing_tasks[admin_id].cancel()
                    except:
                        pass
                    del self.publishing_tasks[admin_id]
                logger.info(f"⏹️ توقف النشر للمشرف {admin_id}")
                return True
            return False
    
    def start_private_reply(self, admin_id: int) -> bool:
        """بدء الرد على الرسائل الخاصة"""
        with self.lock:
            if not self.private_reply_active.get(admin_id, False):
                self.private_reply_active[admin_id] = True
                task = asyncio.create_task(self.handle_private_messages_task(admin_id))
                self.private_reply_tasks[admin_id] = task
                logger.info(f"✅ بدأ الرد في الخاص للمشرف {admin_id}")
                return True
            return False
    
    def stop_private_reply(self, admin_id: int) -> bool:
        """إيقاف الرد على الرسائل الخاصة"""
        with self.lock:
            if self.private_reply_active.get(admin_id, False):
                self.private_reply_active[admin_id] = False
                if admin_id in self.private_reply_tasks:
                    try:
                        self.private_reply_tasks[admin_id].cancel()
                    except:
                        pass
                    del self.private_reply_tasks[admin_id]
                logger.info(f"⏹️ توقف الرد في الخاص للمشرف {admin_id}")
                return True
            return False
    
    def start_group_reply(self, admin_id: int) -> bool:
        """بدء الردود في المجموعات"""
        with self.lock:
            if not self.group_reply_active.get(admin_id, False):
                self.group_reply_active[admin_id] = True
                task = asyncio.create_task(self.handle_group_replies_task(admin_id))
                self.group_reply_tasks[admin_id] = task
                logger.info(f"✅ بدأ الرد في القروبات للمشرف {admin_id}")
                return True
            return False
    
    def stop_group_reply(self, admin_id: int) -> bool:
        """إيقاف الردود في المجموعات"""
        with self.lock:
            if self.group_reply_active.get(admin_id, False):
                self.group_reply_active[admin_id] = False
                if admin_id in self.group_reply_tasks:
                    try:
                        self.group_reply_tasks[admin_id].cancel()
                    except:
                        pass
                    del self.group_reply_tasks[admin_id]
                logger.info(f"⏹️ توقف الرد في القروبات للمشرف {admin_id}")
                return True
            return False
    
    def start_random_reply(self, admin_id: int) -> bool:
        """بدء الردود العشوائية في القروبات"""
        with self.lock:
            if not self.random_reply_active.get(admin_id, False):
                self.random_reply_active[admin_id] = True
                task = asyncio.create_task(self.handle_random_replies_task(admin_id))
                self.random_reply_tasks[admin_id] = task
                logger.info(f"✅ بدأ الرد العشوائي للمشرف {admin_id}")
                return True
            return False
    
    def stop_random_reply(self, admin_id: int) -> bool:
        """إيقاف الردود العشوائية في القروبات"""
        with self.lock:
            if self.random_reply_active.get(admin_id, False):
                self.random_reply_active[admin_id] = False
                if admin_id in self.random_reply_tasks:
                    try:
                        self.random_reply_tasks[admin_id].cancel()
                    except:
                        pass
                    del self.random_reply_tasks[admin_id]
                logger.info(f"⏹️ توقف الرد العشوائي للمشرف {admin_id}")
                return True
            return False
    
    def start_join_groups(self, admin_id: int) -> bool:
        """بدء الانضمام إلى المجموعات"""
        with self.lock:
            if not self.join_groups_active.get(admin_id, False):
                self.join_groups_active[admin_id] = True
                task = asyncio.create_task(self.join_groups_task(admin_id))
                self.join_groups_tasks[admin_id] = task
                logger.info(f"✅ بدأ الانضمام للمجموعات للمشرف {admin_id}")
                return True
            return False
    
    def stop_join_groups(self, admin_id: int) -> bool:
        """إيقاف الانضمام إلى المجموعات"""
        with self.lock:
            if self.join_groups_active.get(admin_id, False):
                self.join_groups_active[admin_id] = False
                if admin_id in self.join_groups_tasks:
                    try:
                        self.join_groups_tasks[admin_id].cancel()
                    except:
                        pass
                    del self.join_groups_tasks[admin_id]
                logger.info(f"⏹️ توقف الانضمام للمجموعات للمشرف {admin_id}")
                return True
            return False
    
    # ============ إحصائيات ومراقبة ============
    
    def get_stats(self) -> Dict[str, Any]:
        """الحصول على الإحصائيات"""
        now = datetime.now()
        uptime = now - self.stats['last_activity']
        
        return {
            'publish_count': self.stats['publish_count'],
            'reply_count': self.stats['reply_count'],
            'join_count': self.stats['join_count'],
            'errors': self.stats['errors'],
            'uptime_seconds': uptime.total_seconds(),
            'last_activity': self.stats['last_activity'].isoformat(),
            'active_tasks': {
                'publishing': sum(1 for v in self.publishing_active.values() if v),
                'private_reply': sum(1 for v in self.private_reply_active.values() if v),
                'group_reply': sum(1 for v in self.group_reply_active.values() if v),
                'random_reply': sum(1 for v in self.random_reply_active.values() if v),
                'join_groups': sum(1 for v in self.join_groups_active.values() if v)
            },
            'cached_clients': len(self.client_cache),
            'delays': self.delay_settings
        }
    
    def reset_stats(self):
        """إعادة تعيين الإحصائيات"""
        self.stats = {
            'publish_count': 0,
            'reply_count': 0,
            'join_count': 0,
            'errors': 0,
            'last_activity': datetime.now()
        }
        logger.info("🔄 تم إعادة تعيين الإحصائيات")
    
    def is_task_running(self, task_type: str, admin_id: int) -> bool:
        """التحقق إذا كانت المهمة تعمل"""
        task_map = {
            'publishing': self.publishing_active,
            'private_reply': self.private_reply_active,
            'group_reply': self.group_reply_active,
            'random_reply': self.random_reply_active,
            'join_groups': self.join_groups_active
        }
        
        if task_type in task_map:
            return task_map[task_type].get(admin_id, False)
        return False
    
    async def stop_all_tasks(self, admin_id: int):
        """إيقاف جميع المهام لمشرف"""
        logger.info(f"🛑 جاري إيقاف جميع المهام للمشرف {admin_id}")
        
        self.stop_publishing(admin_id)
        self.stop_private_reply(admin_id)
        self.stop_group_reply(admin_id)
        self.stop_random_reply(admin_id)
        self.stop_join_groups(admin_id)
        
        # انتظار قليل للتأكد من توقف المهام
        await asyncio.sleep(1)
        
        logger.info(f"✅ تم إيقاف جميع المهام للمشرف {admin_id}")
    
    # ============ معالجات الواجهة ============
    
    async def start_publishing_handler(self, query, context):
        """معالج بدء النشر للواجهة"""
        admin_id = query.from_user.id
        
        if self.start_publishing(admin_id):
            stats = self.get_stats()
            await query.edit_message_text(
                f"🚀 **تم بدء النشر!**\n\n"
                f"📊 **الإحصائيات الحالية:**\n"
                f"• النشر: {stats['publish_count']}\n"
                f"• الردود: {stats['reply_count']}\n"
                f"• الانضمام: {stats['join_count']}\n"
                f"• الأخطاء: {stats['errors']}\n\n"
                f"⏱️ **تأخير نشر القروبات:** {self.delay_settings['publishing']['group_publishing_delay']} ثانية\n"
                f"⚡ **السرعة:** أقصى ما يمكن\n\n"
                f"📡 **المهام النشطة:** {stats['active_tasks']['publishing']}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("⚠️ النشر يعمل بالفعل!")
    
    async def stop_publishing_handler(self, query, context):
        """معالج إيقاف النشر للواجهة"""
        admin_id = query.from_user.id
        
        if self.stop_publishing(admin_id):
            await query.edit_message_text("⏹️ تم إيقاف النشر!")
        else:
            await query.edit_message_text("⚠️ النشر غير نشط!")
    
    async def get_status_handler(self, query, context):
        """معالج الحصول على حالة النظام"""
        admin_id = query.from_user.id
        stats = self.get_stats()
        
        status_text = "📊 **حالة النظام:**\n\n"
        
        status_text += "🔄 **المهام النشطة:**\n"
        for task_name, count in stats['active_tasks'].items():
            task_names = {
                'publishing': 'النشر',
                'private_reply': 'الرد في الخاص',
                'group_reply': 'الرد في القروبات',
                'random_reply': 'الرد العشوائي',
                'join_groups': 'الانضمام للمجموعات'
            }
            emoji = "🟢" if count > 0 else "🔴"
            status_text += f"{emoji} {task_names.get(task_name, task_name)}: {count}\n"
        
        status_text += f"\n📈 **الإحصائيات:**\n"
        status_text += f"📨 النشر: {stats['publish_count']}\n"
        status_text += f"💬 الردود: {stats['reply_count']}\n"
        status_text += f"👥 الانضمام: {stats['join_count']}\n"
        status_text += f"❌ الأخطاء: {stats['errors']}\n"
        
        status_text += f"\n⏱️ **آخر نشاط:** {stats['last_activity']}\n"
        status_text += f"🔗 **العملاء المخبئين:** {stats['cached_clients']}\n"
        
        status_text += f"\n⚙️ **إعدادات التأخير:**\n"
        status_text += f"• نشر القروبات: {self.delay_settings['publishing']['group_publishing_delay']} ثانية\n"
        status_text += f"• بين الإعلانات: {self.delay_settings['publishing']['between_ads']} ثانية\n"
        status_text += f"• بين المجموعات: {self.delay_settings['publishing']['between_groups']} ثانية\n"
        
        await query.edit_message_text(status_text, parse_mode='Markdown')
