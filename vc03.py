"""
VC Player – Ultroid Addon (py-tgcalls + Telethon MTProto)
Commands:
  .play      → reply to audio/video/doc
  .playlist  → show queue
  .skip      → skip current
  .stop      → leave VC + clear
"""

import os
from collections import defaultdict, deque
from pyrogram.types import Message
from . import ultroid_cmd, getLogger

log = getLogger(__name__)

# ----------------------------------------------------------------------
# Telethon MTProto Client for py-tgcalls
from telethon import TelegramClient
from telethon.sessions import StringSession
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import MediaStream, Update

# ----------------------------------------------------------------------
# CONFIGURE YOUR USER SESSION HERE
API_ID = 12345678        # ← Your API ID
API_HASH = "your_api_hash"  # ← Your API HASH
SESSION_STRING = "your_session_string"  # ← Get from .session command

# Create MTProto client
mtproto_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
pytg = PyTgCalls(mtproto_client)

# ----------------------------------------------------------------------
# Global objects
queues: defaultdict[int, deque] = defaultdict(deque)
current: dict[int, dict] = {}

# ----------------------------------------------------------------------
async def ensure_started():
    if not pytg.is_running:
        await mtproto_client.start()
        await pytg.start()
        log.info("py-tgcalls started with MTProto client")

# ----------------------------------------------------------------------
@pytg.on_stream_end()
async def _stream_ended(_: PyTgCalls, update: Update):
    chat_id = update.chat_id
    if queues[chat_id]:
        await _play_next(chat_id)

# ----------------------------------------------------------------------
async def _play_next(chat_id: int, msg: Message | None = None):
    if not queues[chat_id]:
        current.pop(chat_id, None)
        return

    track = queues[chat_id].popleft()
    current[chat_id] = track

    stream = MediaStream(track["path"], video_flags=MediaStream.Flags.IGNORE)

    try:
        await pytg.change_stream(chat_id, stream)
        if msg:
            await msg.edit(f"**Now playing:** `{track['title']}`")
    except Exception as e:
        log.error(f"Play error [{chat_id}]: {e}")
        await _play_next(chat_id, msg)
    finally:
        try:
            os.remove(track["path"])
        except Exception:
            pass

# ----------------------------------------------------------------------
@ultroid_cmd(pattern="play")
async def play_cmd(event: Message):
    reply = event.reply_to_message
    if not reply or not (reply.audio or reply.video or reply.document):
        return await event.edit("**Reply to an audio, video, or document!**")

    await ensure_started()
    chat_id = event.chat.id

    path = await reply.download(in_memory=False)
    if not path:
        return await event.edit("**Download failed.**")

    title = (
        getattr(reply.audio, "title", None) or
        getattr(reply.audio, "file_name", None) or
        getattr(reply.video, "file_name", None) or
        getattr(reply.document, "file_name", None) or
        "Unknown Media"
    )

    track = {"path": path, "title": title}
    queues[chat_id].append(track)
    await event.edit(f"**Queued:** `{title}`")

    stream = MediaStream(path, video_flags=MediaStream.Flags.IGNORE)

    if not await pytg.is_connected(chat_id):
        try:
            await pytg.play(chat_id, stream)
            current[chat_id] = track
            await event.edit(f"**Joined & playing:** `{title}`")
        except Exception as e:
            await event.edit(f"**Join error:** `{e}`")
            try:
                os.remove(path)
            except:
                pass
            queues[chat_id].pop()
            return
    elif chat_id not in current:
        await _play_next(chat_id, event)

# ----------------------------------------------------------------------
@ultroid_cmd(pattern="playlist")
async def playlist_cmd(event: Message):
    chat_id = event.chat.id
    lines = ["**Queue:**\n"]

    if chat_id in current:
        lines.append(f"**Now:** `{current[chat_id]['title']}`\n")

    if queues[chat_id]:
        for i, t in enumerate(queues[chat_id], 1):
            lines.append(f"`{i}.` {t['title']}")
    else:
        lines.append("`empty`")

    await event.edit("\n".join(lines))

# ----------------------------------------------------------------------
@ultroid_cmd(pattern="skip")
async def skip_cmd(event: Message):
    chat_id = event.chat.id
    if chat_id not in current:
        return await event.edit("**Nothing playing.**")

    try:
        os.remove(current[chat_id]["path"])
    except:
        pass
    current.pop(chat_id, None)

    await pytg.change_stream(chat_id, None)
    await _play_next(chat_id, event)
    await event.edit("**Skipped.**")

# ----------------------------------------------------------------------
@ultroid_cmd(pattern="stop")
async def stop_cmd(event: Message):
    chat_id = event.chat.id

    if await pytg.is_connected(chat_id):
        await pytg.leave_group_call(chat_id)

    for t in list(queues[chat_id]):
        try:
            os.remove(t["path"])
        except:
            pass
    queues[chat_id].clear()

    if chat_id in current:
        try:
            os.remove(current[chat_id]["path"])
        except:
            pass
        current.pop(chat_id, None)

    await event.edit("**Stopped & cleared.**")

# ----------------------------------------------------------------------
# Keep alive
idle()
