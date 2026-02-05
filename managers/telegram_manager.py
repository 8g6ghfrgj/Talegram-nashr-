import asyncio
import os
import random
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from config import DELAY_SETTINGS

logger = logging.getLogger(__name__)


class TelegramBotManager:
    def __init__(self, db):
        self.db = db

        self.delay = DELAY_SETTINGS

        # حالات المهام
        self.publishing_active = {}
        self.private_reply_active = {}
        self.group_reply_active = {}
        self.random_reply_active = {}
        self.join_groups_active = {}

        # المهام
        self.tasks = {}

        # الكاش
        self.clients: Dict[str, TelegramClient] = {}

        # إحصائيات
        self.stats = {
            "publish": 0,
            "reply": 0,
            "join": 0,
            "errors": 0,
            "last_activity": datetime.now()
        }

        logger.info("✅ TelegramBotManager جاهز")


    # ================= CLIENT =================

    async def get_client(self, session: str) -> Optional[TelegramClient]:

        if session in self.clients:
            return self.clients[session]

        try:
            client = TelegramClient(StringSession(session), 1, "x")
            await client.connect()

            if not await client.is_user_authorized():
                await client.disconnect()
                return None

            self.clients[session] = client
            return client

        except Exception as e:
            logger.error(f"❌ فشل إنشاء الجلسة: {e}")
            return None


    async def close_client(self, session: str):

        if session in self.clients:
            try:
                await self.clients[session].disconnect()
            except:
                pass
            del self.clients[session]


    async def cleanup_all(self):

        for s in list(self.clients.keys()):
            await self.close_client(s)


    # ================= نشر =================

    async def publishing_task(self, admin_id):

        logger.info(f"🚀 بدأ النشر للمشرف {admin_id}")

        while self.publishing_active.get(admin_id):

            try:
                self.stats["last_activity"] = datetime.now()

                accounts = self.db.get_active_publishing_accounts(admin_id)
                ads = self.db.get_ads(admin_id)

                if not accounts or not ads:
                    await asyncio.sleep(self.delay["publishing"]["between_cycles"])
                    continue

                for acc in accounts:

                    if not self.publishing_active.get(admin_id):
                        break

                    acc_id, session, name, username = acc

                    client = await self.get_client(session)
                    if not client:
                        continue

                    try:
                        dialogs = await client.get_dialogs(limit=50)
                    except:
                        continue

                    groups = [d for d in dialogs if d.is_group or d.is_channel]

                    for dialog in groups:

                        if not self.publishing_active.get(admin_id):
                            break

                        for ad in ads:

                            try:
                                ad_id, ad_type, text, media, *_ = ad

                                if ad_type == "text":
                                    await client.send_message(dialog.id, text)

                                elif ad_type == "photo" and media and os.path.exists(media):
                                    await client.send_file(dialog.id, media, caption=text)

                                elif ad_type == "contact" and media and os.path.exists(media):
                                    await client.send_file(dialog.id, media)

                                self.stats["publish"] += 1
                                self.db.update_account_activity(acc_id)

                                await asyncio.sleep(self.delay["publishing"]["between_ads"])

                            except errors.FloodWaitError as e:
                                await asyncio.sleep(e.seconds + 1)

                            except Exception:
                                self.stats["errors"] += 1

                        await asyncio.sleep(
                            self.delay["publishing"]["group_publishing_delay"]
                        )

                await asyncio.sleep(self.delay["publishing"]["between_cycles"])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ خطأ نشر: {e}")
                await asyncio.sleep(5)

        logger.info(f"⏹️ توقف النشر {admin_id}")


    def start_publishing(self, admin_id):

        if self.publishing_active.get(admin_id):
            return False

        self.publishing_active[admin_id] = True
        self.tasks[f"publish_{admin_id}"] = asyncio.create_task(
            self.publishing_task(admin_id)
        )

        return True


    def stop_publishing(self, admin_id):

        self.publishing_active[admin_id] = False

        task = self.tasks.pop(f"publish_{admin_id}", None)
        if task:
            task.cancel()

        return True


    # ================= رد خاص =================

    async def private_reply_task(self, admin_id):

        while self.private_reply_active.get(admin_id):

            try:
                accounts = self.db.get_active_publishing_accounts(admin_id)
                replies = self.db.get_private_replies(admin_id)

                if not accounts or not replies:
                    await asyncio.sleep(self.delay["private_reply"]["between_cycles"])
                    continue

                for acc in accounts:

                    if not self.private_reply_active.get(admin_id):
                        break

                    acc_id, session, *_ = acc

                    client = await self.get_client(session)
                    if not client:
                        continue

                    msgs = await client.get_messages(None, limit=5)

                    for msg in msgs:
                        if msg.is_private and not msg.out:

                            reply = random.choice(replies)[1]

                            try:
                                await client.send_message(msg.sender_id, reply)
                                self.stats["reply"] += 1
                                self.db.update_account_activity(acc_id)

                            except:
                                pass

                            await asyncio.sleep(
                                self.delay["private_reply"]["between_replies"]
                            )

                await asyncio.sleep(self.delay["private_reply"]["between_cycles"])

            except asyncio.CancelledError:
                break
            except:
                await asyncio.sleep(3)


    def start_private_reply(self, admin_id):

        if self.private_reply_active.get(admin_id):
            return False

        self.private_reply_active[admin_id] = True
        self.tasks[f"private_{admin_id}"] = asyncio.create_task(
            self.private_reply_task(admin_id)
        )

        return True


    def stop_private_reply(self, admin_id):

        self.private_reply_active[admin_id] = False

        task = self.tasks.pop(f"private_{admin_id}", None)
        if task:
            task.cancel()

        return True


    # ================= الانضمام =================

    async def join_groups_task(self, admin_id):

        while self.join_groups_active.get(admin_id):

            try:
                accounts = self.db.get_active_publishing_accounts(admin_id)
                groups = self.db.get_groups(admin_id, status="pending")

                if not accounts or not groups:
                    await asyncio.sleep(self.delay["join_groups"]["between_cycles"])
                    continue

                for acc in accounts:

                    if not self.join_groups_active.get(admin_id):
                        break

                    acc_id, session, name, _ = acc

                    client = await self.get_client(session)
                    if not client:
                        continue

                    for g in groups[:5]:

                        gid, link, *_ = g

                        ok = await self.join_one(client, link)

                        if ok:
                            self.db.update_group_status(gid, "joined")
                            self.stats["join"] += 1
                        else:
                            self.db.update_group_status(gid, "failed")

                        await asyncio.sleep(
                            self.delay["join_groups"]["between_links"]
                        )

                    await self.close_client(session)

                await asyncio.sleep(self.delay["join_groups"]["between_cycles"])

            except asyncio.CancelledError:
                break
            except:
                await asyncio.sleep(5)


    async def join_one(self, client, link):

        try:
            clean = link.replace("https://", "").replace("t.me/", "")

            if clean.startswith("+") or "joinchat" in clean:
                code = clean.split("/")[-1].replace("+", "")
                await client(ImportChatInviteRequest(code))
                return True

            if clean.startswith("@"):
                clean = clean[1:]

            await client(JoinChannelRequest(f"@{clean}"))
            return True

        except errors.UserAlreadyParticipantError:
            return True

        except:
            return False


    def start_join_groups(self, admin_id):

        if self.join_groups_active.get(admin_id):
            return False

        self.join_groups_active[admin_id] = True
        self.tasks[f"join_{admin_id}"] = asyncio.create_task(
            self.join_groups_task(admin_id)
        )

        return True


    def stop_join_groups(self, admin_id):

        self.join_groups_active[admin_id] = False

        task = self.tasks.pop(f"join_{admin_id}", None)
        if task:
            task.cancel()

        return True


    # ================= إحصائيات =================

    def get_stats(self) -> Dict[str, Any]:

        return {
            "publish": self.stats["publish"],
            "reply": self.stats["reply"],
            "join": self.stats["join"],
            "errors": self.stats["errors"],
            "last_activity": self.stats["last_activity"].isoformat(),
            "active": {
                "publishing": sum(self.publishing_active.values()),
                "private_reply": sum(self.private_reply_active.values()),
                "join_groups": sum(self.join_groups_active.values())
            },
            "cached_clients": len(self.clients)
        }


    async def stop_all(self, admin_id):

        self.stop_publishing(admin_id)
        self.stop_private_reply(admin_id)
        self.stop_join_groups(admin_id)

        await asyncio.sleep(1)
