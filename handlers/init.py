"""
حزمة معالجات البوت

تحتوي على جميع الكلاسات المسؤولة عن:
- الحسابات
- الإعلانات
- المجموعات
- الردود
- المشرفين
- المحادثات
"""

from .account_handlers import AccountHandlers
from .ad_handlers import AdHandlers
from .group_handlers import GroupHandlers
from .reply_handlers import ReplyHandlers
from .admin_handlers import AdminHandlers
from .conversation_handlers import ConversationHandlers


__all__ = [
    "AccountHandlers",
    "AdHandlers",
    "GroupHandlers",
    "ReplyHandlers",
    "AdminHandlers",
    "ConversationHandlers",
]


__version__ = "1.0.0"
