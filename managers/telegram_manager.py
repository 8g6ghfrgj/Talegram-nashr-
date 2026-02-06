import asyncio
import logging
import random

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

from config import DELAY_SETTINGS

logger = logging.getLogger(__name__)


# ================= ضع بياناتك هنا =================

API_ID = 123456          # ضع api_id
API_HASH = "API_HASH_HERE"   # ضع api_hash

# ==================================================


class TelegramBotManager:

    def __init__(self, db):
        self.db = db

        self.publishing_tasks = {}
        self.join_tasks = {}

        self.clients = {}

        # مؤقت النشر الافتراضي (ثواني)
        self.publish_delay = 5


    # ==================================================
    # CREATE / GET TELETHON CLIENT
    # ==================================================

    async def get_client(self, session_string):

        if session_string in self.clients:
            return self.clients[session_string]

        client = TelegramClient(
            StringSession(session_string),
            API_ID,
            API_HASH
        )

        await client.connect()

        if not await client.is_user_authorized():
            raise Exception("Session not authorized")

        self.clients[session_string] = client
        return client


    # ==================================================
    # START PUBLISHING
    # ==================================================

    def start_publishing(self, admin_id):

        if admin_id in self.publishing_tasks:
            return False

        task = asyncio.create_task(
            self._publishing_loop(admin_id)
        )

        self.publishing_tasks[admin_id] = task
        return True


    def stop_publishing(self, admin_id):

        task = self.publishing_tasks.pop(admin_id, None)

        if task:
            task.cancel()
            return True

        return False


    # ==================================================
    # REAL PUBLISH LOOP
    # ==================================================

    async def _publishing_loop(self, admin_id):

        logger.info(f"[PUBLISH] Started for admin {admin_id}")

        while True:
            try:
                accounts = self.db.get_accounts(admin_id)
                ads = self.db.get_ads(admin_id)
                groups = self.db.get_groups(admin_id)

                active_accounts = [a for a in accounts if a[3] == 1]
                target_groups = [g for g in groups]

                if not active_accounts or not ads or not target_groups:
                    await asyncio.sleep(10)
                    continue

                random.shuffle(active_accounts)
                random.shuffle(ads)
                random.shuffle(target_groups)

                for acc in active_accounts:

                    session_string = acc[2]

                    try:
                        client = await self.get_client(session_string)
                    except Exception as e:
                        logger.error(f"Session failed: {e}")
                        continue

                    for ad in ads:

                        ad_type = ad[2]
                        ad_text = ad[3]
                        ad_media = ad[4]

                        for group in target_groups:

                            group_link = group[2]

                            try:

                                if ad_type == "text":
                                    await client.send_message(
                                        group_link,
                                        ad_text
                                    )

                                elif ad_type == "photo":
                                    await client.send_file(
                                        group_link,
                                        ad_media,
                                        caption=ad_text
                                    )

                                elif ad_type == "contact":
                                    await client.send_file(
                                        group_link,
                                        ad_media
                                    )

                                logger.info(
                                    f"[SENT] acc:{acc[0]} -> {group_link}"
                                )

                                await asyncio.sleep(self.publish_delay)

                            except FloodWaitError as e:
                                logger.warning(f"FloodWait {e.seconds}s")
                                await asyncio.sleep(e.seconds)

                            except Exception as e:
                                logger.error(f"Send error: {e}")
                                await asyncio.sleep(2)

                await asyncio.sleep(
                    DELAY_SETTINGS["publishing"]["between_cycles"]
                )

            except asyncio.CancelledError:
                logger.info(f"[PUBLISH] Stopped for admin {admin_id}")
                break

            except Exception as e:
                logger.exception(e)
                await asyncio.sleep(5)


    # ==================================================
    # JOIN GROUPS (OPTIONAL REAL LATER)
    # ==================================================

    def start_join_groups(self, admin_id):

        if admin_id in self.join_tasks:
            return False

        task = asyncio.create_task(
            self._join_groups_loop(admin_id)
        )

        self.join_tasks[admin_id] = task
        return True


    def stop_join_groups(self, admin_id):

        task = self.join_tasks.pop(admin_id, None)

        if task:
            task.cancel()
            return True

        return False


    async def _join_groups_loop(self, admin_id):

        while True:
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
