import aiosqlite
import asyncio
from datetime import datetime

from config import DB_NAME


class BotDatabase:

    def __init__(self):
        self.db_name = DB_NAME
        asyncio.get_event_loop().run_until_complete(self._create_tables())


    # ==================================================
    # CONNECTION
    # ==================================================

    async def _connect(self):
        return await aiosqlite.connect(self.db_name)


    # ==================================================
    # CREATE TABLES
    # ==================================================

    async def _create_tables(self):

        async with await self._connect() as db:

            await db.executescript("""

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

            await db.commit()


    # ==================================================
    # HELPERS
    # ==================================================

    def _now(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    # ==================================================
    # ADMINS
    # ==================================================

    def is_admin(self, admin_id):
        return asyncio.get_event_loop().run_until_complete(
            self._is_admin(admin_id)
        )

    async def _is_admin(self, admin_id):

        async with await self._connect() as db:

            cur = await db.execute(
                "SELECT active FROM admins WHERE id=?",
                (admin_id,)
            )
            row = await cur.fetchone()

            return bool(row and row[0])


    def add_admin(self, admin_id, username, role, active):

        return asyncio.get_event_loop().run_until_complete(
            self._add_admin(admin_id, username, role, active)
        )

    async def _add_admin(self, admin_id, username, role, active):

        async with await self._connect() as db:

            try:
                await db.execute(
                    "INSERT OR REPLACE INTO admins VALUES (?,?,?,?,?)",
                    (admin_id, username, role, int(active), self._now())
                )
                await db.commit()
                return True, "OK"
            except Exception as e:
                return False, str(e)


    def get_admins(self):

        return asyncio.get_event_loop().run_until_complete(
            self._get_admins()
        )

    async def _get_admins(self):

        async with await self._connect() as db:

            cur = await db.execute(
                "SELECT * FROM admins ORDER BY added DESC"
            )
            return await cur.fetchall()


    def delete_admin(self, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._delete_admin(admin_id)
        )

    async def _delete_admin(self, admin_id):

        async with await self._connect() as db:

            await db.execute(
                "DELETE FROM admins WHERE id=?",
                (admin_id,)
            )
            await db.commit()
            return True


    def toggle_admin_status(self, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._toggle_admin_status(admin_id)
        )

    async def _toggle_admin_status(self, admin_id):

        async with await self._connect() as db:

            cur = await db.execute(
                "SELECT active FROM admins WHERE id=?",
                (admin_id,)
            )
            row = await cur.fetchone()

            if not row:
                return False

            new_status = 0 if row[0] else 1

            await db.execute(
                "UPDATE admins SET active=? WHERE id=?",
                (new_status, admin_id)
            )

            await db.commit()
            return True


    # ==================================================
    # ACCOUNTS
    # ==================================================

    def add_account(self, admin_id, session):

        return asyncio.get_event_loop().run_until_complete(
            self._add_account(admin_id, session)
        )

    async def _add_account(self, admin_id, session):

        async with await self._connect() as db:

            await db.execute(
                "INSERT INTO accounts VALUES (NULL,?,?,?,?)",
                (admin_id, session, 1, self._now())
            )

            await db.commit()
            return True, "OK"


    def get_accounts(self, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._get_accounts(admin_id)
        )

    async def _get_accounts(self, admin_id):

        async with await self._connect() as db:

            cur = await db.execute(
                "SELECT * FROM accounts WHERE admin_id=? ORDER BY added DESC",
                (admin_id,)
            )

            return await cur.fetchall()


    def delete_account(self, acc_id, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._delete_account(acc_id, admin_id)
        )

    async def _delete_account(self, acc_id, admin_id):

        async with await self._connect() as db:

            await db.execute(
                "DELETE FROM accounts WHERE id=? AND admin_id=?",
                (acc_id, admin_id)
            )

            await db.commit()
            return True


    def toggle_account_status(self, acc_id, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._toggle_account_status(acc_id, admin_id)
        )

    async def _toggle_account_status(self, acc_id, admin_id):

        async with await self._connect() as db:

            cur = await db.execute(
                "SELECT active FROM accounts WHERE id=? AND admin_id=?",
                (acc_id, admin_id)
            )
            row = await cur.fetchone()

            if not row:
                return False

            new_status = 0 if row[0] else 1

            await db.execute(
                "UPDATE accounts SET active=? WHERE id=? AND admin_id=?",
                (new_status, acc_id, admin_id)
            )

            await db.commit()
            return True


    # ==================================================
    # ADS
    # ==================================================

    def add_ad(self, ad_type, text, media, _, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._add_ad(ad_type, text, media, admin_id)
        )

    async def _add_ad(self, ad_type, text, media, admin_id):

        async with await self._connect() as db:

            await db.execute(
                "INSERT INTO ads VALUES (NULL,?,?,?,?,?)",
                (admin_id, ad_type, text, media, self._now())
            )

            await db.commit()
            return True, "OK"


    def get_ads(self, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._get_ads(admin_id)
        )

    async def _get_ads(self, admin_id):

        async with await self._connect() as db:

            cur = await db.execute(
                "SELECT * FROM ads WHERE admin_id=? ORDER BY added DESC",
                (admin_id,)
            )

            return await cur.fetchall()


    def delete_ad(self, ad_id, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._delete_ad(ad_id, admin_id)
        )

    async def _delete_ad(self, ad_id, admin_id):

        async with await self._connect() as db:

            await db.execute(
                "DELETE FROM ads WHERE id=? AND admin_id=?",
                (ad_id, admin_id)
            )

            await db.commit()
            return True


    # ==================================================
    # GROUPS
    # ==================================================

    def add_group(self, admin_id, link):

        return asyncio.get_event_loop().run_until_complete(
            self._add_group(admin_id, link)
        )

    async def _add_group(self, admin_id, link):

        async with await self._connect() as db:

            await db.execute(
                "INSERT INTO groups VALUES (NULL,?,?,?,?)",
                (admin_id, link, "pending", self._now())
            )

            await db.commit()
            return True, "OK"


    def get_groups(self, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._get_groups(admin_id)
        )

    async def _get_groups(self, admin_id):

        async with await self._connect() as db:

            cur = await db.execute(
                "SELECT * FROM groups WHERE admin_id=? ORDER BY added DESC",
                (admin_id,)
            )

            return await cur.fetchall()


    def delete_group(self, group_id, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._delete_group(group_id, admin_id)
        )

    async def _delete_group(self, group_id, admin_id):

        async with await self._connect() as db:

            await db.execute(
                "DELETE FROM groups WHERE id=? AND admin_id=?",
                (group_id, admin_id)
            )

            await db.commit()
            return True


    # ==================================================
    # REPLIES
    # ==================================================

    def add_private_reply(self, admin_id, text):

        return asyncio.get_event_loop().run_until_complete(
            self._add_private_reply(admin_id, text)
        )

    async def _add_private_reply(self, admin_id, text):

        async with await self._connect() as db:

            await db.execute(
                "INSERT INTO private_replies VALUES (NULL,?,?,?)",
                (admin_id, text, self._now())
            )

            await db.commit()
            return True, "OK"


    def get_private_replies(self, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._get_private_replies(admin_id)
        )

    async def _get_private_replies(self, admin_id):

        async with await self._connect() as db:

            cur = await db.execute(
                "SELECT * FROM private_replies WHERE admin_id=? ORDER BY added DESC",
                (admin_id,)
            )

            return await cur.fetchall()


    def delete_private_reply(self, reply_id, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._delete_private_reply(reply_id, admin_id)
        )

    async def _delete_private_reply(self, reply_id, admin_id):

        async with await self._connect() as db:

            await db.execute(
                "DELETE FROM private_replies WHERE id=? AND admin_id=?",
                (reply_id, admin_id)
            )

            await db.commit()
            return True


    def add_random_reply(self, admin_id, r_type, text, media):

        return asyncio.get_event_loop().run_until_complete(
            self._add_random_reply(admin_id, r_type, text, media)
        )

    async def _add_random_reply(self, admin_id, r_type, text, media):

        async with await self._connect() as db:

            await db.execute(
                "INSERT INTO random_replies VALUES (NULL,?,?,?,?,?)",
                (admin_id, r_type, text, media, self._now())
            )

            await db.commit()
            return True, "OK"


    def get_random_replies(self, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._get_random_replies(admin_id)
        )

    async def _get_random_replies(self, admin_id):

        async with await self._connect() as db:

            cur = await db.execute(
                "SELECT * FROM random_replies WHERE admin_id=? ORDER BY added DESC",
                (admin_id,)
            )

            return await cur.fetchall()


    def delete_random_reply(self, reply_id, admin_id):

        return asyncio.get_event_loop().run_until_complete(
            self._delete_random_reply(reply_id, admin_id)
        )

    async def _delete_random_reply(self, reply_id, admin_id):

        async with await self._connect() as db:

            await db.execute(
                "DELETE FROM random_replies WHERE id=? AND admin_id=?",
                (reply_id, admin_id)
            )

            await db.commit()
            return True


    # ==================================================
    # SYSTEM STATS
    # ==================================================

    def get_system_statistics(self):

        return asyncio.get_event_loop().run_until_complete(
            self._get_system_statistics()
        )

    async def _get_system_statistics(self):

        async with await self._connect() as db:

            stats = {}

            for table in [
                "admins",
                "accounts",
                "ads",
                "groups",
                "private_replies",
                "random_replies"
            ]:

                cur = await db.execute(f"SELECT COUNT(*) FROM {table}")
                count = await cur.fetchone()
                stats[table] = count[0]

            return {
                "admins": stats["admins"],
                "accounts": stats["accounts"],
                "ads": stats["ads"],
                "groups": stats["groups"],
                "replies": stats["private_replies"] + stats["random_replies"]
                              }
