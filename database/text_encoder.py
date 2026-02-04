import base64
import random
import logging

logger = logging.getLogger(__name__)

class TextEncoder:
    """فئة متقدمة لتشفير وفك تشفير النصوص"""
    
    @staticmethod
    def encode_text(text):
        """
        تشفير النص باستخدام تقنيات متعددة متداخلة
        """
        try:
            if not text or not isinstance(text, str):
                return text
            
            # 1. تحويل النص إلى بايتات
            text_bytes = text.encode('utf-8')
            
            # 2. Base64 Encoding
            base64_encoded = base64.b64encode(text_bytes).decode('utf-8')
            
            # 3. Reverse text
            reversed_text = text[::-1]
            
            # 4. إنشاء مفتاح عشوائي
            key = random.randint(1, 255)
            
            # 5. XOR encoding
            xor_encoded = ''.join(chr(ord(c) ^ key) for c in text)
            
            # 6. Rot13 encoding للنص العكسي
            rot13_reversed = ''
            for char in reversed_text:
                if 'a' <= char <= 'z':
                    rot13_reversed += chr((ord(char) - ord('a') + 13) % 26 + ord('a'))
                elif 'A' <= char <= 'Z':
                    rot13_reversed += chr((ord(char) - ord('A') + 13) % 26 + ord('A'))
                elif 'أ' <= char <= 'ي':
                    # Rot13 للعربية
                    rot13_reversed += chr((ord(char) - ord('أ') + 13) % 28 + ord('أ'))
                else:
                    rot13_reversed += char
            
            # 7. Combine multiple encodings with salt
            salt = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
            
            combined = f"B64:{base64_encoded}|REV:{rot13_reversed}|XOR:{xor_encoded}|KEY:{key}|SALT:{salt}"
            
            # 8. Double Base64 encoding
            final_encoded = base64.b64encode(combined.encode('utf-8')).decode('utf-8')
            
            # 9. إضافة علامة التحقق
            checksum = sum(ord(c) for c in final_encoded) % 1000
            final_result = f"TEXTV1-{final_encoded}-{checksum:03d}"
            
            return final_result
            
        except Exception as e:
            logger.error(f"خطأ في تشفير النص: {str(e)}")
            return text
    
    @staticmethod
    def decode_text(encoded_text):
        """
        فك تشفير النص المشفر
        """
        try:
            if not encoded_text or not isinstance(encoded_text, str):
                return encoded_text
            
            # التحقق من التنسيق
            if not encoded_text.startswith("TEXTV1-") or encoded_text.count('-') != 2:
                # محاولة فك تشفير النص القديم
                return TextEncoder._decode_legacy(encoded_text)
            
            # استخراج الأجزاء
            parts = encoded_text.split('-')
            if len(parts) != 3:
                return encoded_text
            
            main_encoded = parts[1]
            checksum = int(parts[2])
            
            # التحقق من checksum
            current_checksum = sum(ord(c) for c in main_encoded) % 1000
            if current_checksum != checksum:
                logger.warning("Checksum mismatch - possible data corruption")
            
            # فك Base64 المزدوج
            decoded = base64.b64decode(main_encoded.encode('utf-8')).decode('utf-8')
            
            # استخراج الأجزاء
            parts_dict = {}
            for part in decoded.split('|'):
                if ':' in part:
                    key, value = part.split(':', 1)
                    parts_dict[key] = value
            
            # محاولة فك التشفير من XOR أولاً
            if 'XOR' in parts_dict and 'KEY' in parts_dict:
                try:
                    key = int(parts_dict['KEY'])
                    xor_decoded = ''.join(chr(ord(c) ^ key) for c in parts_dict['XOR'])
                    return xor_decoded
                except:
                    pass
            
            # محاولة فك Rot13 للنص العكسي
            if 'REV' in parts_dict:
                try:
                    rot13_text = parts_dict['REV']
                    # فك Rot13
                    original_reversed = ''
                    for char in rot13_text:
                        if 'a' <= char <= 'z':
                            original_reversed += chr((ord(char) - ord('a') - 13) % 26 + ord('a'))
                        elif 'A' <= char <= 'Z':
                            original_reversed += chr((ord(char) - ord('A') - 13) % 26 + ord('A'))
                        elif 'أ' <= char <= 'ي':
                            original_reversed += chr((ord(char) - ord('أ') - 13) % 28 + ord('أ'))
                        else:
                            original_reversed += char
                    
                    # عكس النص
                    return original_reversed[::-1]
                except:
                    pass
            
            # استخدام Base64 الأساسي
            if 'B64' in parts_dict:
                try:
                    return base64.b64decode(parts_dict['B64']).decode('utf-8')
                except:
                    pass
            
            # إذا فشل كل شيء، إرجاع النص الأصلي
            return decoded
            
        except Exception as e:
            logger.error(f"خطأ في فك تشفير النص: {str(e)}")
            return encoded_text
    
    @staticmethod
    def _decode_legacy(encoded_text):
        """فك تشفير النص القديم (للتوافق مع الإصدارات السابقة)"""
        try:
            decoded = base64.b64decode(encoded_text.encode('utf-8')).decode('utf-8')
            
            parts = {}
            for part in decoded.split('|'):
                if ':' in part:
                    key, value = part.split(':', 1)
                    parts[key] = value
            
            if 'XOR' in parts and 'KEY' in parts:
                key = int(parts['KEY'])
                xor_decoded = ''.join(chr(ord(c) ^ key) for c in parts['XOR'])
                return xor_decoded
            
            if 'B64' in parts:
                return base64.b64decode(parts['B64']).decode('utf-8')
            
            return decoded
        except:
            return encoded_text
    
    @staticmethod
    def create_hash(text, length=16):
        """إنشاء هاش للنص"""
        import hashlib
        
        if not text:
            return ''
        
        # إنشاء هاش SHA256
        hash_object = hashlib.sha256(text.encode())
        hex_dig = hash_object.hexdigest()
        
        # تقصير الهاش للطول المطلوب
        return hex_dig[:length]
    
    @staticmethod
    def encrypt_file(file_path, output_path=None):
        """تشفير ملف"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # تشفير المحتوى
            encoded_content = base64.b64encode(content)
            
            output = output_path or file_path + '.enc'
            with open(output, 'wb') as f:
                f.write(encoded_content)
            
            return True, output
        except Exception as e:
            logger.error(f"خطأ في تشفير الملف: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def decrypt_file(file_path, output_path=None):
        """فك تشفير ملف"""
        try:
            with open(file_path, 'rb') as f:
                encoded_content = f.read()
            
            # فك تشفير المحتوى
            content = base64.b64decode(encoded_content)
            
            output = output_path or file_path.replace('.enc', '')
            with open(output, 'wb') as f:
                f.write(content)
            
            return True, output
        except Exception as e:
            logger.error(f"خطأ في فك تشفير الملف: {str(e)}")
            return False, str(e)
