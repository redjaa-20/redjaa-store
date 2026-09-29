"""
Reproduksi: /start sebagai admin — cek apakah keyboard 🔧 Admin Panel muncul.
Pakai registrasi handler ASLI dari main(). Temp file.
"""
import asyncio
import os
import sys

os.environ["TELEGRAM_BOT_TOKEN"] = "1:FAKE"

import warnings
warnings.filterwarnings("ignore")
import logging
logging.disable(logging.CRITICAL)

import database as db

db.DB_FILE = "_dbg_start.json"
if os.path.exists("_dbg_start.json"):
    os.remove("_dbg_start.json")

import config
import bot

# Pakai ADMIN_ID ASLI dari .env (jangan di-override)
TEST_ADMIN_ID = config.ADMIN_ID
print("ADMIN_ID asli dari .env =", TEST_ADMIN_ID)
print("is_admin(ADMIN_ID)      =", bot.is_admin(TEST_ADMIN_ID))

from telegram import Update, Message, Chat, User, MessageEntity
from telegram.ext import Application
from telegram.request import HTTPXRequest

OUT = []


class FakeBot:
    id = 999
    username = "testbot"
    first_name = "TestBot"

    def _mk(self, chat_id, text=None, caption=None, mid=1):
        return Message(message_id=mid, date=None,
                       chat=Chat(id=chat_id, type=Chat.PRIVATE),
                       text=text, caption=caption)

    async def send_message(self, chat_id, text, reply_markup=None, **kw):
        OUT.append(("send_message", chat_id, text, reply_markup))
        return self._mk(chat_id, text=text)

    async def send_photo(self, chat_id, photo, caption=None, reply_markup=None, **kw):
        OUT.append(("send_photo", chat_id, caption, reply_markup))
        return self._mk(chat_id, caption=caption, mid=2)

    async def send_document(self, chat_id, document, caption=None, reply_markup=None, **kw):
        OUT.append(("send_document", chat_id, caption, reply_markup))
        return self._mk(chat_id, caption=caption, mid=3)

    async def send_chat_action(self, *a, **kw):
        pass

    async def answer_callback_query(self, *a, **kw):
        return True

    async def edit_message_text(self, text, chat_id=None, message_id=None, **kw):
        return self._mk(chat_id or 1, text=text)

    async def edit_message_caption(self, caption=None, chat_id=None, **kw):
        return self._mk(chat_id or 1, caption=caption)

    async def edit_message_reply_markup(self, *a, **kw):
        return True

    async def delete_message(self, *a, **kw):
        return True

    async def get_me(self):
        return User(id=999, first_name="TestBot", is_bot=True)

    async def set_my_commands(self, *a, **kw):
        pass

    async def delete_webhook(self, *a, **kw):
        pass

    async def initialize(self):
        pass


# ---------------------------------------------------------------
# Bangun app dan jalankan main() sampai updater start
# ---------------------------------------------------------------
created = {}


async def fake_initialize(self):
    created["app"] = self


Application.initialize = fake_initialize
Application.start = lambda self: asyncio.sleep(0)
Application.stop = lambda self: asyncio.sleep(0)
Application.shutdown = lambda self: asyncio.sleep(0)

from telegram.ext import Updater

Updater.start_polling = lambda self, **kw: (_ for _ in ()).throw(KeyboardInterrupt())
Updater.stop = lambda self: asyncio.sleep(0)

bot.set_bot_commands = lambda app: asyncio.sleep(0)


async def main():
    try:
        await bot.main()
    except (KeyboardInterrupt, SystemExit):
        pass

    app = created["app"]
    if app is None:
        print("!! app tidak terbentuk")
        sys.exit(1)

    app.bot = FakeBot()
    await app.bot.initialize()
    # Tandai app sebagai sudah di-initialize (kita pakai bot palsu)
    app._initialized = True
    app._running = True

    # Instrumentasi: apakah start() benar-benar dipanggil?
    orig_start = bot.start
    calls = []

    async def traced_start(update, context):
        uid = update.effective_user.id
        calls.append(("start_called", uid, bot.is_admin(uid)))
        print(f"\n>>> start() DIPANGGIL untuk uid={uid}, is_admin={bot.is_admin(uid)}")
        return await orig_start(update, context)

    # Ganti callback di entry_points ConversationHandler /start
    patched = 0
    for g, hs in app.handlers.items():
        for h in hs:
            for ep in getattr(h, "entry_points", []):
                if getattr(ep, "callback", None) is orig_start:
                    ep.callback = traced_start
                    patched += 1
                    print(f">>> patched entry_point di group {g}")
    print(f">>> total entry point dipatch: {patched}")

    print("\n" + "=" * 62)
    print("UJI /start SEBAGAI ADMIN")
    print("=" * 62)

    chat = Chat(id=TEST_ADMIN_ID, type=Chat.PRIVATE)
    user = User(id=TEST_ADMIN_ID, first_name="Admin", is_bot=False)
    m = Message(message_id=1, date=None, chat=chat, from_user=user, text="/start",
                entities=[MessageEntity(type=MessageEntity.BOT_COMMAND, offset=0, length=6)])
    m.set_bot(app.bot)
    u = Update(update_id=1, message=m)
    u.set_bot(app.bot)

    OUT.clear()
    await app.process_update(u)

    print(f"\n>>> Calls logged: {calls}")
    if not calls:
        print("!!! start() TIDAK dipanggil — /start tidak terhandle oleh command handler")
    else:
        print("\n" + "=" * 62)
    for kind, chat_id, text, rm in OUT:
        print(f"\n--- {kind} ke {chat_id} ---")
        print("TEXT:", (text or "")[:200].replace("\n", " | "))
        if rm is not None and hasattr(rm, "keyboard"):
            print("KEYBOARD:")
            for row in rm.keyboard:
                print("   ", [b.text for b in row])
        elif rm is not None:
            print("REPLY_MARKUP:", rm)

    # Cek eksplisit
    print("\n" + "=" * 62)
    found_admin_btn = False
    for kind, chat_id, text, rm in OUT:
        if rm is not None and hasattr(rm, "keyboard"):
            labels = [b.text for row in rm.keyboard for b in row]
            if "🔧 Admin Panel" in labels:
                found_admin_btn = True
    print("Tombol 🔧 Admin Panel muncul di /start admin:", found_admin_btn)
    print("=" * 62)


if __name__ == "__main__":
    asyncio.run(main())
