import sqlite3
from datetime import datetime
from typing import List, Tuple


DB_NAME = "bot_database.db"


class BotDatabase:

    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()


    # ==================================================
    # CREATE TABLES
    # ==================================================

    def _create_tables(self):

        cursor = self.conn.cursor()

        # ---------- ADMINS ----------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT,
            active INTEGER,
            added_at TEXT
        )
        """)

        # ---------- ACCOUNTS ----------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            session TEXT,
            active INTEGER,
            added_at TEXT
        )
        """)

        # ---------- ADS ----------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            type TEXT,
            text TEXT,
            media_path TEXT,
            added_at TEXT
        )
        """)

        # ---------- GROUPS ----------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            link TEXT,
            status TEXT,
            added_at TEXT
        )
        """)

        # ---------- PRIVATE REPLIES ----------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS private_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            text TEXT,
            added_at TEXT
        )
        """)

        # ---------- RANDOM REPLIES ----------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS random_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            type TEXT,
            text TEXT,
            media_path TEXT,
            added_at TEXT
        )
        """)

        self.conn.commit()


    # ==================================================
    # ADMINS
    # ==================================================

    def add_admin(self, admin_id: int, username: str, role: str, active: bool = True):

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT OR IGNORE INTO admins (id, username, role, active, added_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            admin_id,
            username,
            role,
            1 if active else 0,
            datetime.now().isoformat()
        ))

        self.conn.commit()
        return True, "OK"


    def is_admin(self, admin_id: int) -> bool:

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM admins WHERE id=? AND active=1",
            (admin_id,)
        )

        return cursor.fetchone() is not None


    def get_admins(self) -> List[Tuple]:

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM admins")
        return cursor.fetchall()


    def delete_admin(self, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM admins WHERE id=?", (admin_id,))
        self.conn.commit()


    # ==================================================
    # ACCOUNTS
    # ==================================================

    def add_account(self, admin_id: int, session: str):

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO accounts (admin_id, session, active, added_at)
        VALUES (?, ?, 1, ?)
        """, (
            admin_id,
            session,
            datetime.now().isoformat()
        ))

        self.conn.commit()
        return True, "OK"


    def get_accounts(self, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM accounts WHERE admin_id=?",
            (admin_id,)
        )
        return cursor.fetchall()


    def toggle_account_status(self, account_id: int, admin_id: int):

        cursor = self.conn.cursor()

        cursor.execute("""
        UPDATE accounts
        SET active = CASE WHEN active=1 THEN 0 ELSE 1 END
        WHERE id=? AND admin_id=?
        """, (account_id, admin_id))

        self.conn.commit()


    def delete_account(self, account_id: int, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM accounts WHERE id=? AND admin_id=?",
            (account_id, admin_id)
        )
        self.conn.commit()


    # ==================================================
    # ADS
    # ==================================================

    def add_ad(self, ad_type: str, text: str, media_path: str, _unused, admin_id: int):

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO ads (admin_id, type, text, media_path, added_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            admin_id,
            ad_type,
            text,
            media_path,
            datetime.now().isoformat()
        ))

        self.conn.commit()
        return True, "OK"


    def get_ads(self, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM ads WHERE admin_id=?",
            (admin_id,)
        )
        return cursor.fetchall()


    def delete_ad(self, ad_id: int, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM ads WHERE id=? AND admin_id=?",
            (ad_id, admin_id)
        )
        self.conn.commit()


    # ==================================================
    # GROUPS
    # ==================================================

    def add_group(self, admin_id: int, link: str):

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO groups (admin_id, link, status, added_at)
        VALUES (?, ?, 'pending', ?)
        """, (
            admin_id,
            link,
            datetime.now().isoformat()
        ))

        self.conn.commit()
        return True, "OK"


    def get_groups(self, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM groups WHERE admin_id=?",
            (admin_id,)
        )
        return cursor.fetchall()


    def delete_group(self, group_id: int, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM groups WHERE id=? AND admin_id=?",
            (group_id, admin_id)
        )
        self.conn.commit()


    # ==================================================
    # PRIVATE REPLIES
    # ==================================================

    def add_private_reply(self, admin_id: int, text: str):

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO private_replies (admin_id, text, added_at)
        VALUES (?, ?, ?)
        """, (
            admin_id,
            text,
            datetime.now().isoformat()
        ))

        self.conn.commit()


    def get_private_replies(self, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM private_replies WHERE admin_id=?",
            (admin_id,)
        )
        return cursor.fetchall()


    def delete_private_reply(self, reply_id: int, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM private_replies WHERE id=? AND admin_id=?",
            (reply_id, admin_id)
        )
        self.conn.commit()


    # ==================================================
    # RANDOM REPLIES
    # ==================================================

    def add_random_reply(self, admin_id: int, r_type: str, text: str, media_path: str):

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO random_replies (admin_id, type, text, media_path, added_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            admin_id,
            r_type,
            text,
            media_path,
            datetime.now().isoformat()
        ))

        self.conn.commit()


    def get_random_replies(self, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM random_replies WHERE admin_id=?",
            (admin_id,)
        )
        return cursor.fetchall()


    def delete_random_reply(self, reply_id: int, admin_id: int):

        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM random_replies WHERE id=? AND admin_id=?",
            (reply_id, admin_id)
        )
        self.conn.commit()
