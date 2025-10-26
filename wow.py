# < Stealth One-Time Media Saver > 
# Trigger: .wow (or .wow anything)
# No edits, no replies → 100% invisible

import os, asyncio, random, string
from datetime import datetime
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.errors import MessageNotModifiedError

from . import ultroid_cmd, client, LOGS

DL_DIR = "resources/downloads/onetime"
os.makedirs(DL_DIR, exist_ok=True)

def rnd_name(path):
    if not os.path.exists(path): return path
    b, e = os.path.splitext(path)
    return f"{b}_{''.join(random.choices(string.ascii_lowercase, k=5))}{e}"

@ultroid_cmd(
    pattern="wow(?: |$)(.*)",
    disable_errors=True,  # Don't show errors to user
    invisible=True        # No command response
)
async def _stealth_save_onetime(e):
    # --- Silent: No reply, no edit ---
    me = await client.get_me()
    saved_chat = me.id
    saved = 0

    try:
        async for m in client.iter_messages(e.chat_id, limit=20):
            if not m or not m.media or not getattr(m.media, "ttl_seconds", None):
                continue

            # --- Get sender name safely ---
            try:
                chat = await client.get_entity(e.chat_id)
                chat_name = getattr(chat, "title", None) or getattr(chat, "first_name", "PM")
            except:
                chat_name = "PM"

            # --- File type ---
            if isinstance(m.media, MessageMediaPhoto):
                pref, ext = "photo", ".jpg"
            elif isinstance(m.media, MessageMediaDocument):
                mime = (m.media.document.mime_type or "").lower()
                if "video" in mime:
                    pref, ext = "video", ".mp4"
                elif mime == "image/gif":
                    pref, ext = "gif", ".gif"
                else:
                    pref, ext = "media", ".webm"
            else:
                continue

            ts = int(datetime.now().timestamp())
            local_name = f"{pref}_{m.id}_{ts}{ext}"
            local_path = rnd_name(os.path.join(DL_DIR, local_name))

            try:
                # --- Force download (critical for one-time) ---
                dl = await client.download_media(
                    m,
                    file=local_path,
                    thumb=-1,
                    # NO progress callback → silent
                )

                if not dl or not os.path.exists(dl):
                    continue

                # --- Forward silently to Saved Messages ---
                await client.send_file(
                    saved_chat,
                    dl,
                    caption=f"One-time • [{chat_name}](https://t.me/c/{str(e.chat_id)[4:]}/{m.id})",
                    silent=True
                )
                saved += 1

            except MessageNotModifiedError:
                continue  # Already viewed
            except Exception as ex:
                LOGS.debug(f"[wow] Failed ID {m.id}: {ex}")
                if os.path.exists(local_path):
                    os.remove(local_path)
                continue

        # --- Optional: Log to your own logs ---
        if saved:
            LOGS.info(f"[wow] Saved {saved} one-time media from chat {e.chat_id}")

    except Exception as err:
        LOGS.error(f"[wow] Fatal error: {err}")

    # --- No output, no edit, no reply → invisible ---
