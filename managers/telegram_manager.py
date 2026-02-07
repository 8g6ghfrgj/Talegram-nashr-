import asyncio
import logging
import random

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)


# =========================
# TELETHON CREDENTIALS
# =========================

API_ID = 123456        # ضع api_id
API_HASH = "API_HASH" # ضع api_hash


# =========================
# TELEGRAM MANAGER
# =========================

class TelegramBotManager:

    def __init__(self, db):
        self.db = db

        # admin_id -> asyncio.Task
        self.publish_tasks = {}

        # session_string -> TelegramClient
        self.clients = {}

        # default delay (seconds)
        self.publish_delay = 5.0


    # ==================================================
    # CLIENT HANDLING
    # ==================================================

    async def get_client(self, session_string: str) -> TelegramClient:

        if session_string in self.clients:
            return self.clients[session_string]

        client = TelegramClient(
            StringSession(session_string),
            API_ID,
            API_HASH
        )

        await client.connect()

        if not await client.is_user_authorized():
            raise RuntimeError("Session not authorized")

        self.clients[session_string] = client
        return client


    # ==================================================
    # START / STOP PUBLISHING
    # ==================================================

    def start_publishing(self, admin_id: int) -> bool:

        if admin_id in self.publish_tasks:
            return False  # already running

        task = asyncio.create_task(
            self._publish_loop(admin_id)
        )

        self.publish_tasks[admin_id] = task
        logger.info(f"[PUBLISH] Started for admin {admin_id}")
        return True


    def stop_publishing(self, admin_id: int) -> bool:

        task = self.publish_tasks.pop(admin_id, None)

        if not task:
            return False

        task.cancel()
        logger.info(f"[PUBLISH] Stopped for admin {admin_id}")
        return True


    # ==================================================
    # MAIN PUBLISH LOOP (REAL)
    # ==================================================

    async def _publish_loop(self, admin_id: int):

        try:
            while True:

                accounts = self.db.get_accounts(admin_id)
                ads = self.db.get_ads(admin_id)
                groups = self.db.get_groups(admin_id)

                active_accounts = [a for a in accounts if a[3] == 1]

                if not active_accounts or not ads or not groups:
                    await asyncio.sleep(10)
                    continue

                random.shuffle(active_accounts)
                random.shuffle(ads)
                random.shuffle(groups)

                for acc in active_accounts:

                    session_string = acc[2]

                    try:
                        client = await self.get_client(session_string)
                    except Exception as e:
                        logger.error(f"[SESSION ERROR] {e}")
                        continue

                    for ad in ads:

                        ad_type = ad[2]
                        ad_text = ad[3]
                        ad_media = ad[4]

                        for group in groups:

                            group_link = group[2]

                            try:
                                if ad_type == "text":
                                    await client.send_message(group_link, ad_text)

                                elif ad_type == "photo":
                                    await client.send_file(
                                        group_link,
                                        ad_media,
                                        caption=ad_text
                                    )

                                elif ad_type == "contact":
                                    await client.send_file(group_link, ad_media)

                                logger.info(
                                    f"[SENT] acc={acc[0]} -> {group_link}"
                                )

                                await asyncio.sleep(self.publish_delay)

                            except FloodWaitError as e:
                                logger.warning(f"[FLOODWAIT] {e.seconds}s")
                                await asyncio.sleep(e.seconds)

                            except Exception as e:
                                logger.error(f"[SEND ERROR] {e}")
                                await asyncio.sleep(3)

                # pause between cycles
                await asyncio.sleep(30)

        except asyncio.CancelledError:
            logger.info(f"[PUBLISH LOOP CANCELLED] admin {admin_id}")

        except Exception as e:
            logger.exception(f"[PUBLISH LOOP ERROR] {e}")


    # ==================================================
    # CLEANUP (OPTIONAL)
    # ==================================================

    async def shutdown(self):

        for task in self.publish_tasks.values():
            task.cancel()

        for client in self.clients.values():
            await client.disconnect()

        self.publish_tasks.clear()
        self.clients.clear()
