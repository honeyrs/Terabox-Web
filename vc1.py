"""
VC Player – Play replied audio/video in voice chat
Uses: py-tgcalls (pip install -U py-tgcalls)
Commands: .play (reply), .playlist, .skip, .stop
"""

import os
from collections import defaultdict, deque
from pyrogram.types import Message

from . import ultroid_cmd, client, get_logger

log = get_logger(__name__)

# Import py-tgcalls
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, Update

# Initialize
pytg = PyTgCalls(client)

# Queue system
queues = defaultdict(deque)
current = {}

# Ensure started
async def ensure_started():
    if not pytg.is_running:
        await pytg.start()

# Auto-play next
@pytg.on_stream_end()
async def on_stream_end(_, update: Update):
    chat_id = update.chat_id
    if queues[chat_id]:
        await play_next(chat_id)

async def play_next(chat_id: int, msg: Message | None = None):
    if not queues[chat_id]:
        current.pop(chat_id, None)
        return

    track = queues[chat_id].popleft()
    current[chat_id] = track

    try:
        await pytg.change_stream(chat_id, AudioPiped(track["path"]))
        if msg:
            await msg.edit(f"**Now playing:** `{track['title']}`")
    except Exception as e:
        log.error(f"Play error: {e}")
        await play_next(chat_id, msg)
    finally:
        try:
            os.remove(track["path"])
        except:
            pass

# ——————————————————————— COMMANDS ———————————————————————

@ultroid_cmd(pattern="play")
async def play(event: Message):
    reply = event.reply_to_message
    if not reply or not (reply.audio or reply.video):
        return await event.edit("**Reply to an audio or video file!**")

    await ensure_started()
    chat_id = event.chat.id

    path = await reply.download(in_memory=False)
    if not path:
        return await event.edit("**Download failed.**")

    title = (
        reply.audio.title or reply.audio.file_name or
        reply.video.file_name or "Unknown Media"
    )

    track = {"path": path, "title": title}
    queues[chat_id].append(track)
    await event.edit(f"**Queued:** `{title}`")

    if not pytg.is_connected(chat_id):
        try:
            await pytg.join_group_call(chat_id, AudioPiped(path))
            current[chat_id] = track
            await event.edit(f"**Joined VC & playing:** `{title}`")
        except Exception as e:
            await event.edit(f"**Join error:** `{e}`")
            os.remove(path)
            queues[chat_id].pop()
    elif chat_id not in current:
        await play_next(chat_id, event)

@ultroid_cmd(pattern="playlist")
async def playlist(event: Message):
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

@ultroid_cmd(pattern="skip")
async def skip(event: Message):
    chat_id = event.chat.id
    if chat_id not in current:
        return await event.edit("**Nothing playing.**")

    try:
        os.remove(current[chat_id]["path"])
    except:
        pass
    current.pop(chat_id, None)

    await pytg.change_stream(chat_id, None)
    await play_next(chat_id, event)
    await event.edit("**Skipped.**")

@ultroid_cmd(pattern="stop")
async def stop(event: Message):
    chat_id = event.chat.id
    if pytg.is_connected(chat_id):
        await pytg.leave_group_call(chat_id)

    for t in list(queues[chat_id]):
        try:
            os.remove(t["path"])
        except:
            pass
    queues[chat_id].clear()
    current.pop(chat_id, None)
    await event.edit("**Stopped & cleared.**")
