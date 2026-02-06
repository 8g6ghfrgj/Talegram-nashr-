import sqlite3
from datetime import datetime
from config import DB_NAME


class BotDatabase:

    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.cur = self.conn.cursor()
        self.create_tables()


    # ==================================================
    # TABLES
    # ==================================================

    def create_tables(self):

        self.cur.executescript("""

        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT,
            active INTEGER,
            added TEXT
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            session TEXT,
            active INTEGER,
            added TEXT
        );

        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            type TEXT,
            text TEXT,
            media TEXT,
            added TEXT
        );

        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            link TEXT,
            status TEXT,
            added TEXT
        );

        CREATE TABLE IF NOT EXISTS private_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            text TEXT,
            added TEXT
        );

        CREATE TABLE IF NOT EXISTS random_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            type TEXT,
            text TEXT,
            media TEXT,
            added TEXT
        );

        """)

        self.conn.commit()


    def now(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    # ==================================================
    # ADMINS
    # ==================================================

    def is_admin(self, admin_id):
        self.cur.execute(
            "SELECT active FROM admins WHERE id=?",
            (admin_id,)
        )
        row = self.cur.fetchone()
        return bool(row and row[0])


    def add_admin(self, admin_id, username, role, active):
        self.cur.execute(
            "INSERT OR REPLACE INTO admins VALUES (?,?,?,?,?)",
            (admin_id, username, role, int(active), self.now())
        )
        self.conn.commit()
        return True, "OK"


    def get_admins(self):
        self.cur.execute("SELECT * FROM admins ORDER BY added DESC")
        return self.cur.fetchall()


    def delete_admin(self, admin_id):
        self.cur.execute("DELETE FROM admins WHERE id=?", (admin_id,))
        self.conn.commit()
        return True


    def toggle_admin_status(self, admin_id):
        self.cur.execute("SELECT active FROM admins WHERE id=?", (admin_id,))
        row = self.cur.fetchone()

        if not row:
            return False

        new_status = 0 if row[0] else 1

        self.cur.execute(
            "UPDATE admins SET active=? WHERE id=?",
            (new_status, admin_id)
        )

        self.conn.commit()
        return True


    # ==================================================
    # ACCOUNTS
    # ==================================================

    def add_account(self, admin_id, session):
        self.cur.execute(
            "INSERT INTO accounts VALUES (NULL,?,?,?,?)",
            (admin_id, session, 1, self.now())
        )
        self.conn.commit()
        return True, "OK"


    def get_accounts(self, admin_id):
        self.cur.execute(
            "SELECT * FROM accounts WHERE admin_id=? ORDER BY added DESC",
            (admin_id,)
        )
        return self.cur.fetchall()


    def delete_account(self, acc_id, admin_id):
        self.cur.execute(
            "DELETE FROM accounts WHERE id=? AND admin_id=?",
            (acc_id, admin_id)
        )
        self.conn.commit()
        return True


    def toggle_account_status(self, acc_id, admin_id):

        self.cur.execute(
            "SELECT active FROM accounts WHERE id=? AND admin_id=?",
            (acc_id, admin_id)
        )
        row = self.cur.fetchone()

        if not row:
            return False

        new_status = 0 if row[0] else 1

        self.cur.execute(
            "UPDATE accounts SET active=? WHERE id=? AND admin_id=?",
            (new_status, acc_id, admin_id)
        )

        self.conn.commit()
        return True


    # ==================================================
    # ADS
    # ==================================================

    def add_ad(self, ad_type, text, media, _, admin_id):

        self.cur.execute(
            "INSERT INTO ads VALUES (NULL,?,?,?,?,?)",
            (admin_id, ad_type, text, media, self.now())
        )

        self.conn.commit()
        return True, "OK"


    def get_ads(self, admin_id):

        self.cur.execute(
            "SELECT * FROM ads WHERE admin_id=? ORDER BY added DESC",
            (admin_id,)
        )

        return self.cur.fetchall()


    def delete_ad(self, ad_id, admin_id):

        self.cur.execute(
            "DELETE FROM ads WHERE id=? AND admin_id=?",
            (ad_id, admin_id)
        )

        self.conn.commit()
        return True


    # ==================================================
    # GROUPS
    # ==================================================

    def add_group(self, admin_id, link):

        self.cur.execute(
            "INSERT INTO groups VALUES (NULL,?,?,?,?)",
            (admin_id, link, "pending", self.now())
        )

        self.conn.commit()
        return True, "OK"


    def get_groups(self, admin_id):

        self.cur.execute(
            "SELECT * FROM groups WHERE admin_id=? ORDER BY added DESC",
            (admin_id,)
        )

        return self.cur.fetchall()


    def delete_group(self, group_id, admin_id):

        self.cur.execute(
            "DELETE FROM groups WHERE id=? AND admin_id=?",
            (group_id, admin_id)
        )

        self.conn.commit()
        return True


    # ==================================================
    # REPLIES
    # ==================================================

    def add_private_reply(self, admin_id, text):

        self.cur.execute(
            "INSERT INTO private_replies VALUES (NULL,?,?,?)",
            (admin_id, text, self.now())
        )

        self.conn.commit()
        return True, "OK"


    def get_private_replies(self, admin_id):

        self.cur.execute(
            "SELECT * FROM private_replies WHERE admin_id=? ORDER BY added DESC",
            (admin_id,)
        )

        return self.cur.fetchall()


    def delete_private_reply(self, reply_id, admin_id):

        self.cur.execute(
            "DELETE FROM private_replies WHERE id=? AND admin_id=?",
            (reply_id, admin_id)
        )

        self.conn.commit()
        return True


    def add_random_reply(self, admin_id, r_type, text, media):

        self.cur.execute(
            "INSERT INTO random_replies VALUES (NULL,?,?,?,?,?)",
            (admin_id, r_type, text, media, self.now())
        )

        self.conn.commit()
        return True, "OK"


    def get_random_replies(self, admin_id):

        self.cur.execute(
            "SELECT * FROM random_replies WHERE admin_id=? ORDER BY added DESC",
            (admin_id,)
        )

        return self.cur.fetchall()


    def delete_random_reply(self, reply_id, admin_id):

        self.cur.execute(
            "DELETE FROM random_replies WHERE id=? AND admin_id=?",
            (reply_id, admin_id)
        )

        self.conn.commit()
        return True


    # ==================================================
    # SYSTEM STATS
    # ==================================================

    def get_system_statistics(self):

        tables = [
            "admins",
            "accounts",
            "ads",
            "groups",
            "private_replies",
            "random_replies"
        ]

        stats = {}

        for table in tables:
            self.cur.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = self.cur.fetchone()[0]

        return {
            "admins": stats["admins"],
            "accounts": stats["accounts"],
            "ads": stats["ads"],
            "groups": stats["groups"],
            "replies": stats["private_replies"] + stats["random_replies"]
        }
