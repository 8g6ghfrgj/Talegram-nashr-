import sqlite3
import os
import logging
from datetime import datetime
from .text_encoder import TextEncoder

logger = logging.getLogger(__name__)

class BotDatabase:
    def __init__(self, db_name="bot_database.db"):
        """تهيئة قاعدة البيانات"""
        self.db_name = db_name
        self.text_encoder = TextEncoder()
        self.init_database()
        logger.info(f"✅ تم تهيئة قاعدة البيانات: {db_name}")
    
    def init_database(self):
        """إنشاء جداول قاعدة البيانات"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # جدول الحسابات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_string TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    name TEXT,
                    username TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER DEFAULT 0,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول الإعلانات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    text TEXT,
                    media_path TEXT,
                    file_type TEXT,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER DEFAULT 0,
                    is_encoded BOOLEAN DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # جدول المجموعات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    join_date DATETIME,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER DEFAULT 0,
                    last_checked DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول المشرفين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_super_admin BOOLEAN DEFAULT 0,
                    can_add_accounts BOOLEAN DEFAULT 1,
                    can_add_ads BOOLEAN DEFAULT 1,
                    can_add_groups BOOLEAN DEFAULT 1,
                    can_manage_replies BOOLEAN DEFAULT 1
                )
            ''')
            
            # جدول الردود الخاصة
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS private_replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reply_text TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER DEFAULT 0,
                    is_encoded BOOLEAN DEFAULT 1
                )
            ''')
            
            # جدول الردود الجماعية النصية
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_text_replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger TEXT NOT NULL,
                    reply_text TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER DEFAULT 0,
                    is_encoded BOOLEAN DEFAULT 1
                )
            ''')
            
            # جدول الردود الجماعية مع الصور
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_photo_replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger TEXT NOT NULL,
                    reply_text TEXT,
                    media_path TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER DEFAULT 0,
                    is_encoded BOOLEAN DEFAULT 1
                )
            ''')
            
            # جدول الردود العشوائية في القروبات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_random_replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reply_text TEXT,
                    media_path TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER DEFAULT 0,
                    is_encoded BOOLEAN DEFAULT 1,
                    has_media BOOLEAN DEFAULT 0,
                    probability INTEGER DEFAULT 100  -- احتمالية الرد (100% افتراضياً)
                )
            ''')
            
            # جدول نشر الحسابات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_publishing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'active',
                    last_publish DATETIME,
                    publish_count INTEGER DEFAULT 0,
                    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE
                )
            ''')
            
            # جدول المجموعات المجمعة
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bulk_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    link TEXT NOT NULL,
                    name TEXT,
                    status TEXT DEFAULT 'pending',
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER DEFAULT 0,
                    last_attempt DATETIME
                )
            ''')
            
            # جدول السجلات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("✅ تم إنشاء جميع جداول قاعدة البيانات")
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء جداول قاعدة البيانات: {e}")
            raise
        finally:
            conn.close()
    
    # ============ إدارة الحسابات ============
    
    def add_account(self, session_string, phone, name, username, admin_id=0):
        """إضافة حساب جديد"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO accounts (session_string, phone, name, username, admin_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_string, phone, name, username, admin_id))
            
            account_id = cursor.lastrowid
            
            # إضافة إلى جدول النشر
            cursor.execute('''
                INSERT INTO account_publishing (account_id)
                VALUES (?)
            ''', (account_id,))
            
            conn.commit()
            
            # تسجيل النشاط
            self.log_action(admin_id, "add_account", f"تم إضافة حساب جديد: {name}")
            
            return True, f"✅ تم إضافة الحساب بنجاح (ID: {account_id})"
            
        except sqlite3.IntegrityError:
            return False, "❌ هذا الحساب مضاف مسبقاً"
        except Exception as e:
            logger.error(f"خطأ في إضافة الحساب: {e}")
            return False, f"❌ خطأ في إضافة الحساب: {str(e)}"
        finally:
            conn.close()
    
    def get_accounts(self, admin_id=None, active_only=True):
        """الحصول على جميع الحسابات"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            query = '''
                SELECT a.id, a.session_string, a.phone, a.name, a.username, 
                       a.is_active, a.added_date, ap.status, ap.last_publish
                FROM accounts a
                LEFT JOIN account_publishing ap ON a.id = ap.account_id
                WHERE 1=1
            '''
            
            params = []
            
            if admin_id is not None:
                query += ' AND (a.admin_id = ? OR a.admin_id = 0)'
                params.append(admin_id)
            
            if active_only:
                query += ' AND a.is_active = 1'
            
            query += ' ORDER BY a.id'
            
            cursor.execute(query, params)
            accounts = cursor.fetchall()
            
            return accounts
            
        except Exception as e:
            logger.error(f"خطأ في جلب الحسابات: {e}")
            return []
        finally:
            conn.close()
    
    def get_active_publishing_accounts(self, admin_id=None):
        """الحصول على الحسابات النشطة للنشر"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            query = '''
                SELECT a.id, a.session_string, a.name, a.username
                FROM accounts a
                JOIN account_publishing ap ON a.id = ap.account_id
                WHERE ap.status = 'active' AND a.is_active = 1
            '''
            
            params = []
            
            if admin_id is not None:
                query += ' AND (a.admin_id = ? OR a.admin_id = 0)'
                params.append(admin_id)
            
            cursor.execute(query, params)
            accounts = cursor.fetchall()
            
            return accounts
            
        except Exception as e:
            logger.error(f"خطأ في جلب الحسابات النشطة: {e}")
            return []
        finally:
            conn.close()
    
    def delete_account(self, account_id, admin_id=None):
        """حذف حساب"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id:
                cursor.execute('DELETE FROM accounts WHERE id = ? AND (admin_id = ? OR admin_id = 0)', 
                             (account_id, admin_id))
            else:
                cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
            
            cursor.execute('DELETE FROM account_publishing WHERE account_id = ?', (account_id,))
            
            conn.commit()
            
            # تسجيل النشاط
            self.log_action(admin_id, "delete_account", f"تم حذف حساب ID: {account_id}")
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطأ في حذف الحساب: {e}")
            return False
        finally:
            conn.close()
    
    def update_account_activity(self, account_id):
        """تحديث وقت آخر نشاط للحساب"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE accounts 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (account_id,))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تحديث نشاط الحساب: {e}")
            return False
        finally:
            conn.close()
    
    # ============ إدارة الإعلانات ============
    
    def add_ad(self, ad_type, text=None, media_path=None, file_type=None, admin_id=0):
        """إضافة إعلان"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # تشفير النص إذا كان موجوداً
            encoded_text = self.text_encoder.encode_text(text) if text else None
            
            cursor.execute('''
                INSERT INTO ads (type, text, media_path, file_type, admin_id, is_encoded)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ad_type, encoded_text, media_path, file_type, admin_id, 1 if text else 0))
            
            conn.commit()
            
            # تسجيل النشاط
            self.log_action(admin_id, "add_ad", f"تم إضافة إعلان نوع: {ad_type}")
            
            return True, f"✅ تم إضافة الإعلان بنجاح"
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الإعلان: {e}")
            return False, f"❌ خطأ في إضافة الإعلان: {str(e)}"
        finally:
            conn.close()
    
    def get_ads(self, admin_id=None, decode=True):
        """الحصول على جميع الإعلانات"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id is not None:
                cursor.execute('SELECT * FROM ads WHERE admin_id = ? OR admin_id = 0 ORDER BY id', (admin_id,))
            else:
                cursor.execute('SELECT * FROM ads ORDER BY id')
            
            ads = cursor.fetchall()
            
            # فك تشفير النصوص إذا طُلب
            if decode:
                decoded_ads = []
                for ad in ads:
                    ad_list = list(ad)
                    if ad_list[2] and ad_list[6]:  # النص وكان مشفراً
                        try:
                            ad_list[2] = self.text_encoder.decode_text(ad_list[2])
                        except:
                            pass
                    decoded_ads.append(tuple(ad_list))
                return decoded_ads
            
            return ads
            
        except Exception as e:
            logger.error(f"خطأ في جلب الإعلانات: {e}")
            return []
        finally:
            conn.close()
    
    def delete_ad(self, ad_id, admin_id=None):
        """حذف إعلان"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id:
                cursor.execute('DELETE FROM ads WHERE id = ? AND (admin_id = ? OR admin_id = 0)', 
                             (ad_id, admin_id))
            else:
                cursor.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
            
            conn.commit()
            
            # تسجيل النشاط
            self.log_action(admin_id, "delete_ad", f"تم حذف إعلان ID: {ad_id}")
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطأ في حذف الإعلان: {e}")
            return False
        finally:
            conn.close()
    
    # ============ إدارة المجموعات ============
    
    def add_group(self, link, admin_id=0):
        """إضافة مجموعة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO groups (link, admin_id)
                VALUES (?, ?)
            ''', (link, admin_id))
            
            conn.commit()
            
            # تسجيل النشاط
            self.log_action(admin_id, "add_group", f"تم إضافة مجموعة: {link}")
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إضافة المجموعة: {e}")
            return False
        finally:
            conn.close()
    
    def get_groups(self, admin_id=None, status=None):
        """الحصول على جميع المجموعات"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            query = 'SELECT * FROM groups WHERE 1=1'
            params = []
            
            if admin_id is not None:
                query += ' AND (admin_id = ? OR admin_id = 0)'
                params.append(admin_id)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY id'
            
            cursor.execute(query, params)
            groups = cursor.fetchall()
            
            return groups
            
        except Exception as e:
            logger.error(f"خطأ في جلب المجموعات: {e}")
            return []
        finally:
            conn.close()
    
    def update_group_status(self, group_id, status):
        """تحديث حالة المجموعة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE groups 
                SET status = ?, join_date = CURRENT_TIMESTAMP, last_checked = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, group_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تحديث حالة المجموعة: {e}")
            return False
        finally:
            conn.close()
    
    # ============ إدارة المشرفين ============
    
    def is_owner(self, user_id):
        """التحقق إذا كان المستخدم هو المالك"""
        from config import OWNER_ID
        return user_id == OWNER_ID
    
    def is_admin(self, user_id):
        """التحقق إذا كان المستخدم مشرف"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id FROM admins WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result is not None
        finally:
            conn.close()
    
    def is_super_admin(self, user_id):
        """التحقق إذا كان المستخدم مشرف رئيسي"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id FROM admins WHERE user_id = ? AND is_super_admin = 1', (user_id,))
            result = cursor.fetchone()
            return result is not None
        finally:
            conn.close()
    
    def add_admin(self, user_id, username, full_name, is_super_admin=False):
        """إضافة مشرف - يجب أن يكون المستخدم هو المالك"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO admins (user_id, username, full_name, is_super_admin)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, full_name, is_super_admin))
            
            conn.commit()
            return True, "✅ تم إضافة المشرف بنجاح"
            
        except sqlite3.IntegrityError:
            return False, "❌ هذا المشرف مضاف مسبقاً"
        except Exception as e:
            logger.error(f"خطأ في إضافة المشرف: {e}")
            return False, f"❌ خطأ في إضافة المشرف: {str(e)}"
        finally:
            conn.close()
    
    def get_admins(self):
        """الحصول على جميع المشرفين"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM admins ORDER BY id')
            admins = cursor.fetchall()
            return admins
        except Exception as e:
            logger.error(f"خطأ في جلب المشرفين: {e}")
            return []
        finally:
            conn.close()
    
    def delete_admin(self, admin_id):
        """حذف مشرف - يجب أن يكون المستخدم هو المالك"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM admins WHERE id = ?', (admin_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في حذف المشرف: {e}")
            return False
        finally:
            conn.close()
    
    # ============ إدارة الردود ============
    
    def add_private_reply(self, reply_text, admin_id=0):
        """إضافة رد خاص"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            encoded_text = self.text_encoder.encode_text(reply_text)
            
            cursor.execute('''
                INSERT INTO private_replies (reply_text, admin_id, is_encoded)
                VALUES (?, ?, ?)
            ''', (encoded_text, admin_id, 1))
            
            conn.commit()
            
            # تسجيل النشاط
            self.log_action(admin_id, "add_private_reply", "تم إضافة رد خاص")
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الرد الخاص: {e}")
            return False
        finally:
            conn.close()
    
    def get_private_replies(self, admin_id=None, decode=True):
        """الحصول على الردود الخاصة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id is not None:
                cursor.execute('SELECT * FROM private_replies WHERE admin_id = ? OR admin_id = 0 ORDER BY id', (admin_id,))
            else:
                cursor.execute('SELECT * FROM private_replies ORDER BY id')
            
            replies = cursor.fetchall()
            
            # فك تشفير النصوص
            if decode:
                decoded_replies = []
                for reply in replies:
                    reply_list = list(reply)
                    if reply_list[1] and reply_list[5]:  # النص وكان مشفراً
                        try:
                            reply_list[1] = self.text_encoder.decode_text(reply_list[1])
                        except:
                            pass
                    decoded_replies.append(tuple(reply_list))
                return decoded_replies
            
            return replies
            
        except Exception as e:
            logger.error(f"خطأ في جلب الردود الخاصة: {e}")
            return []
        finally:
            conn.close()
    
    def delete_private_reply(self, reply_id, admin_id=None):
        """حذف رد خاص"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id:
                cursor.execute('DELETE FROM private_replies WHERE id = ? AND (admin_id = ? OR admin_id = 0)', 
                             (reply_id, admin_id))
            else:
                cursor.execute('DELETE FROM private_replies WHERE id = ?', (reply_id,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطأ في حذف الرد الخاص: {e}")
            return False
        finally:
            conn.close()
    
    def add_group_text_reply(self, trigger, reply_text, admin_id=0):
        """إضافة رد نصي جماعي"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            encoded_reply = self.text_encoder.encode_text(reply_text)
            
            cursor.execute('''
                INSERT INTO group_text_replies (trigger, reply_text, admin_id, is_encoded)
                VALUES (?, ?, ?, ?)
            ''', (trigger, encoded_reply, admin_id, 1))
            
            conn.commit()
            
            # تسجيل النشاط
            self.log_action(admin_id, "add_group_text_reply", f"تم إضافة رد نصي: {trigger}")
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الرد النصي: {e}")
            return False
        finally:
            conn.close()
    
    def get_group_text_replies(self, admin_id=None, decode=True):
        """الحصول على الردود النصية الجماعية"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id is not None:
                cursor.execute('SELECT * FROM group_text_replies WHERE admin_id = ? OR admin_id = 0 ORDER BY id', (admin_id,))
            else:
                cursor.execute('SELECT * FROM group_text_replies ORDER BY id')
            
            replies = cursor.fetchall()
            
            # فك تشفير النصوص
            if decode:
                decoded_replies = []
                for reply in replies:
                    reply_list = list(reply)
                    if reply_list[2] and reply_list[6]:  # النص وكان مشفراً
                        try:
                            reply_list[2] = self.text_encoder.decode_text(reply_list[2])
                        except:
                            pass
                    decoded_replies.append(tuple(reply_list))
                return decoded_replies
            
            return replies
            
        except Exception as e:
            logger.error(f"خطأ في جلب الردود النصية: {e}")
            return []
        finally:
            conn.close()
    
    def delete_group_text_reply(self, reply_id, admin_id=None):
        """حذف رد نصي جماعي"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id:
                cursor.execute('DELETE FROM group_text_replies WHERE id = ? AND (admin_id = ? OR admin_id = 0)', 
                             (reply_id, admin_id))
            else:
                cursor.execute('DELETE FROM group_text_replies WHERE id = ?', (reply_id,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطأ في حذف الرد النصي: {e}")
            return False
        finally:
            conn.close()
    
    def add_group_photo_reply(self, trigger, reply_text, media_path, admin_id=0):
        """إضافة رد جماعي مع صورة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            encoded_reply = self.text_encoder.encode_text(reply_text) if reply_text else None
            
            cursor.execute('''
                INSERT INTO group_photo_replies (trigger, reply_text, media_path, admin_id, is_encoded)
                VALUES (?, ?, ?, ?, ?)
            ''', (trigger, encoded_reply, media_path, admin_id, 1 if reply_text else 0))
            
            conn.commit()
            
            # تسجيل النشاط
            self.log_action(admin_id, "add_group_photo_reply", f"تم إضافة رد مع صورة: {trigger}")
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الرد مع صورة: {e}")
            return False
        finally:
            conn.close()
    
    def get_group_photo_replies(self, admin_id=None, decode=True):
        """الحصول على الردود الجماعية مع الصور"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id is not None:
                cursor.execute('SELECT * FROM group_photo_replies WHERE admin_id = ? OR admin_id = 0 ORDER BY id', (admin_id,))
            else:
                cursor.execute('SELECT * FROM group_photo_replies ORDER BY id')
            
            replies = cursor.fetchall()
            
            # فك تشفير النصوص
            if decode:
                decoded_replies = []
                for reply in replies:
                    reply_list = list(reply)
                    if reply_list[2] and reply_list[7]:  # النص وكان مشفراً
                        try:
                            reply_list[2] = self.text_encoder.decode_text(reply_list[2])
                        except:
                            pass
                    decoded_replies.append(tuple(reply_list))
                return decoded_replies
            
            return replies
            
        except Exception as e:
            logger.error(f"خطأ في جلب الردود مع الصور: {e}")
            return []
        finally:
            conn.close()
    
    def delete_group_photo_reply(self, reply_id, admin_id=None):
        """حذف رد جماعي مع صورة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id:
                cursor.execute('DELETE FROM group_photo_replies WHERE id = ? AND (admin_id = ? OR admin_id = 0)', 
                             (reply_id, admin_id))
            else:
                cursor.execute('DELETE FROM group_photo_replies WHERE id = ?', (reply_id,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطأ في حذف الرد مع صورة: {e}")
            return False
        finally:
            conn.close()
    
    def add_group_random_reply(self, reply_text, media_path=None, admin_id=0):
        """إضافة رد عشوائي في القروبات"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            encoded_reply = self.text_encoder.encode_text(reply_text) if reply_text else None
            
            cursor.execute('''
                INSERT INTO group_random_replies (reply_text, media_path, admin_id, is_encoded, has_media)
                VALUES (?, ?, ?, ?, ?)
            ''', (encoded_reply, media_path, admin_id, 1 if reply_text else 0, 1 if media_path else 0))
            
            conn.commit()
            
            # تسجيل النشاط
            self.log_action(admin_id, "add_group_random_reply", "تم إضافة رد عشوائي")
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الرد العشوائي: {e}")
            return False
        finally:
            conn.close()
    
    def get_group_random_replies(self, admin_id=None, decode=True):
        """الحصول على الردود العشوائية في القروبات"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id is not None:
                cursor.execute('SELECT * FROM group_random_replies WHERE (admin_id = ? OR admin_id = 0) AND is_active = 1 ORDER BY id', (admin_id,))
            else:
                cursor.execute('SELECT * FROM group_random_replies WHERE is_active = 1 ORDER BY id')
            
            replies = cursor.fetchall()
            
            # فك تشفير النصوص
            if decode:
                decoded_replies = []
                for reply in replies:
                    reply_list = list(reply)
                    if reply_list[1] and reply_list[6]:  # النص وكان مشفراً
                        try:
                            reply_list[1] = self.text_encoder.decode_text(reply_list[1])
                        except:
                            pass
                    decoded_replies.append(tuple(reply_list))
                return decoded_replies
            
            return replies
            
        except Exception as e:
            logger.error(f"خطأ في جلب الردود العشوائية: {e}")
            return []
        finally:
            conn.close()
    
    def delete_group_random_reply(self, reply_id, admin_id=None):
        """حذف رد عشوائي في القروبات"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if admin_id:
                cursor.execute('DELETE FROM group_random_replies WHERE id = ? AND (admin_id = ? OR admin_id = 0)', 
                             (reply_id, admin_id))
            else:
                cursor.execute('DELETE FROM group_random_replies WHERE id = ?', (reply_id,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطأ في حذف الرد العشوائي: {e}")
            return False
        finally:
            conn.close()
    
    # ============ إدارة المجموعات المجمعة ============
    
    def add_bulk_groups(self, groups_data, admin_id=0):
        """إضافة مجموعات مجمعة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            for link, name in groups_data:
                cursor.execute('''
                    INSERT INTO bulk_groups (link, name, admin_id)
                    VALUES (?, ?, ?)
                ''', (link, name, admin_id))
            
            conn.commit()
            
            # تسجيل النشاط
            self.log_action(admin_id, "add_bulk_groups", f"تم إضافة {len(groups_data)} مجموعة مجمعة")
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إضافة المجموعات المجمعة: {e}")
            return False
        finally:
            conn.close()
    
    def get_bulk_groups(self, admin_id=None, status=None):
        """الحصول على المجموعات المجمعة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            query = 'SELECT * FROM bulk_groups WHERE 1=1'
            params = []
            
            if admin_id is not None:
                query += ' AND (admin_id = ? OR admin_id = 0)'
                params.append(admin_id)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY id'
            
            cursor.execute(query, params)
            groups = cursor.fetchall()
            
            return groups
            
        except Exception as e:
            logger.error(f"خطأ في جلب المجموعات المجمعة: {e}")
            return []
        finally:
            conn.close()
    
    def update_bulk_group_status(self, group_id, status):
        """تحديث حالة المجموعة المجمعة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE bulk_groups 
                SET status = ?, last_attempt = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, group_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تحديث حالة المجموعة المجمعة: {e}")
            return False
        finally:
            conn.close()
    
    # ============ إدارة السجلات ============
    
    def log_action(self, admin_id, action, details=None):
        """تسجيل نشاط"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO logs (admin_id, action, details)
                VALUES (?, ?, ?)
            ''', (admin_id, action, details))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تسجيل النشاط: {e}")
            return False
        finally:
            conn.close()
    
    def get_logs(self, limit=100):
        """الحصول على السجلات"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM logs 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            logs = cursor.fetchall()
            return logs
            
        except Exception as e:
            logger.error(f"خطأ في جلب السجلات: {e}")
            return []
        finally:
            conn.close()
    
    # ============ إحصائيات ============
    
    def get_statistics(self, admin_id=None):
        """الحصول على إحصائيات النظام"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # إحصائيات الحسابات
            query_accounts = '''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active
                FROM accounts
            '''
            
            if admin_id is not None:
                query_accounts += ' WHERE admin_id = ? OR admin_id = 0'
                cursor.execute(query_accounts, (admin_id,))
            else:
                cursor.execute(query_accounts)
            
            accounts_stats = cursor.fetchone()
            stats['accounts'] = {
                'total': accounts_stats[0] or 0,
                'active': accounts_stats[1] or 0
            }
            
            # إحصائيات الإعلانات
            query_ads = 'SELECT COUNT(*) FROM ads'
            if admin_id is not None:
                query_ads += ' WHERE admin_id = ? OR admin_id = 0'
                cursor.execute(query_ads, (admin_id,))
            else:
                cursor.execute(query_ads)
            
            stats['ads'] = cursor.fetchone()[0] or 0
            
            # إحصائيات المجموعات
            query_groups = '''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'joined' THEN 1 ELSE 0 END) as joined
                FROM groups
            '''
            
            if admin_id is not None:
                query_groups += ' WHERE admin_id = ? OR admin_id = 0'
                cursor.execute(query_groups, (admin_id,))
            else:
                cursor.execute(query_groups)
            
            groups_stats = cursor.fetchone()
            stats['groups'] = {
                'total': groups_stats[0] or 0,
                'joined': groups_stats[1] or 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"خطأ في جلب الإحصائيات: {e}")
            return {}
        finally:
            conn.close()
    
    # ============ وظائف التنظيف ============
    
    def cleanup_old_data(self, days=30):
        """تنظيف البيانات القديمة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # حذف السجلات القديمة
            cursor.execute('''
                DELETE FROM logs 
                WHERE timestamp < datetime('now', ?)
            ''', (f'-{days} days',))
            
            deleted_logs = cursor.rowcount
            
            conn.commit()
            
            logger.info(f"✅ تم تنظيف {deleted_logs} سجل قديم")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تنظيف البيانات: {e}")
            return False
        finally:
            conn.close()
    
    def backup_database(self, backup_path):
        """نسخ احتياطي لقاعدة البيانات"""
        try:
            import shutil
            shutil.copy2(self.db_name, backup_path)
            logger.info(f"✅ تم إنشاء نسخة احتياطية في: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {e}")
            return False
