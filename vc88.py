"""
VC Player – pytgcalls v4+ (GitHub) – FULLY WORKING
Commands:
  .play      → queue & play (reply to audio/video/document)
  .playlist  → show queue + current track
  .skip      → skip current
  .stop      → leave VC + clear everything
"""

import os
import asyncio
from collections import defaultdict, deque
from pyrogram.types import Message
from . import ultroid_cmd, vcClient, getLogger

log = getLogger(__name__)

# ----------------------------------------------------------------------
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, HighQualityAudio

# ----------------------------------------------------------------------
# Global client
client = PyTgCalls(vcClient)
queues: defaultdict[int, deque] = defaultdict(deque)
current: dict[int, dict] = {}
active_calls: set[int] = set()

# Start the client
asyncio.create_task(client.start())

# ----------------------------------------------------------------------
async def _on_stream_end(chat_id: int):
    """Called when stream ends"""
    if chat_id in current:
        path = current[chat_id]["path"]
        try:
            os.remove(path)
        except Exception:
            pass
        current.pop(chat_id, None)
    active_calls.discard(chat_id)

    if queues[chat_id]:
        await _play_next(chat_id)
    else:
        try:
            await client.leave_group_call(chat_id)
        except Exception:
            pass

# ----------------------------------------------------------------------
async def _play_next(chat_id: int, msg: Message | None = None):
    if chat_id in active_calls:
        return  # Already playing

    if not queues[chat_id]:
        return

    track = queues[chat_id].popleft()
    path = track["path"]
    title = track["title"]

    active_calls.add(chat_id)
    current[chat_id] = {"path": path, "title": title}

    try:
        await client.join_group_call(
            chat_id,
            AudioPiped(path, HighQualityAudio()),
            stream_type="pulse"
        )

        if msg:
            await msg.edit(f"**Now playing:** `{title}`")

        # Wait until disconnected or manually stopped
        while chat_id in active_calls and client.is_connected(chat_id):
            await asyncio.sleep(1)

        await _on_stream_end(chat_id)

    except Exception as e:
        log.error(f"Play error: {e}")
        await _on_stream_end(chat_id)
        if msg:
            await msg.edit("**Failed to play.**")

# ----------------------------------------------------------------------
@ultroid_cmd(pattern="play")
async def play_cmd(event: Message):
    reply = event.reply_to_message
    if not reply or not (reply.audio or reply.video or reply.document):
        return await event.edit("**Reply to audio/video/document!**")

    chat_id = event.chat.id

    path = await reply.download(in_memory=False)
    if not path:
        return await event.edit("**Download failed.**")

    title = (
        getattr(reply.audio, "title", None)
        or getattr(reply.audio, "file_name", None)
        or getattr(reply.video, "file_name", None)
        or getattr(reply.document, "file_name", None)
        or "Unknown"
    )

    queues[chat_id].append({"path": path, "title": title})
    await event.edit(f"**Queued:** `{title}`")

    if chat_id not in active_calls:
        asyncio.create_task(_play_next(chat_id, event))

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
        await client.leave_group_call(chat_id)
    except Exception:
        pass

    path = current[chat_id]["path"]
    try:
        os.remove(path)
    except Exception:
        pass

    current.pop(chat_id, None)
    active_calls.discard(chat_id)

    await event.edit("**Skipped.**")

    if queues[chat_id]:
        asyncio.create_task(_play_next(chat_id, event))

# ----------------------------------------------------------------------
@ultroid_cmd(pattern="stop")
async def stop_cmd(event: Message):
    chat_id = event.chat.id

    if chat_id in current:
        try:
            await client.leave_group_call(chat_id)
        except Exception:
            pass

        path = current[chat_id]["path"]
        try:
            os.remove(path)
        except Exception:
            pass

        current.pop(chat_id, None)
        active_calls.discard(chat_id)

    for t in list(queues[chat_id]):
        try:
            os.remove(t["path"])
        except Exception:
            pass
    queues[chat_id].clear()

    await event.edit("**Stopped & cleared.**")
