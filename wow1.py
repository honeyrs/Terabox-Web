# < Stealth One-Time Media Saver >
# Trigger: .wow (or .wow anything)
# 100% invisible – no edit, no reply

import os
import asyncio
import random
import string
from datetime import datetime

from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.errors import MessageNotModifiedError

from . import ultroid_cmd, ultroid_bot as client, LOGS  # ← Correct import

DL_DIR = "resources/downloads/onetime"
os.makedirs(DL_DIR, exist_ok=True)


def rnd_name(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    return f"{base}_{''.join(random.choices(string.ascii_lowercase, k=5))}{ext}"


@ultroid_cmd(
    pattern="wow(?: |$)(.*)",
    invisible=True,        # No response
    disable_errors=True,   # Hide errors from user
)
async def stealth_save_onetime(event):
    me = await client.get_me()
    saved_chat = me.id
    saved_count = 0

    try:
        async for msg in client.iter_messages(event.chat_id, limit=20):
            if not msg or not msg.media or not getattr(msg.media, "ttl_seconds", None):
                continue

            # --- Get chat name safely ---
            try:
                chat = await client.get_entity(event.chat_id)
                chat_name = getattr(chat, "title", None) or getattr(chat, "first_name", "PM")
            except:
                chat_name = "PM"

            # --- Detect file type ---
            if isinstance(msg.media, MessageMediaPhoto):
                prefix, ext = "photo", ".jpg"
            elif isinstance(msg.media, MessageMediaDocument):
                mime = (msg.media.document.mime_type or "").lower()
                if "video" in mime:
                    prefix, ext = "video", ".mp4"
                elif mime == "image/gif":
                    prefix, ext = "gif", ".gif"
                else:
                    prefix, ext = "media", ".webm"
            else:
                continue

            timestamp = int(datetime.now().timestamp())
            filename = f"{prefix}_{msg.id}_{timestamp}{ext}"
            filepath = rnd_name(os.path.join(DL_DIR, filename))

            try:
                # --- Force download (critical for one-time media) ---
                downloaded = await client.download_media(
                    msg,
                    file=filepath,
                    thumb=-1,  # Bypass cache
                )

                if not downloaded or not os.path.exists(downloaded):
                    continue

                # --- Send to Saved Messages (silent) ---
                await client.send_file(
                    entity=saved_chat,
                    file=downloaded,
                    caption=f"One-time • [{chat_name}](https://t.me/c/{str(event.chat_id)[4:]}/{msg.id})",
                    silent=True,
                )
                saved_count += 1

                # Optional: delete local file after saving
                # os.remove(downloaded)

            except MessageNotModifiedError:
                continue  # Already viewed
            except Exception as ex:
                LOGS.debug(f"[wow] Failed to save ID {msg.id}: {ex}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                continue

        if saved_count:
            LOGS.info(f"[wow] Saved {saved_count} one-time media from chat {event.chat_id}")

    except Exception as err:
        LOGS.error(f"[wow] Fatal error: {err}")

    # --- NO OUTPUT → 100% STEALTH ---
