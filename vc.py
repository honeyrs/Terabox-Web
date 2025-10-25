"""
VC Play - Play Replied Audio/Video in Voice Chat with Queue
Commands:
.play (reply to audio/video) - Queue and play in VC
.playlist - Show queue
.skip - Skip current track
.stop - Stop and clear queue
No external deps beyond pytgcalls.
"""

from pyrogram import filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioVideoPiped
from pytgcalls.types import Update
import os
import asyncio
from collections import defaultdict, deque

from utilroid import ultroid_cmd, client

# Initialize PyTgCalls
pytgcalls = PyTgCalls(client)

# Queues: chat_id -> deque of {"path": str, "title": str}
queues = defaultdict(deque)

# Current playing: chat_id -> {"path": str, "title": str}
current = {}

# Ensure started
async def ensure_started():
    if not pytgcalls.is_running:
        await pytgcalls.start()

@pytgcalls.on_stream_end()
async def on_end(client: PyTgCalls, update: Update):
    chat_id = update.chat_id
    if queues[chat_id]:
        await play_next(chat_id)
    else:
        current.pop(chat_id, None)
        # Optionally leave VC if queue empty
        # await pytgcalls.leave_group_call(chat_id)

async def play_next(chat_id: int, event: Message = None):
    if not queues[chat_id]:
        if event:
            await event.edit("**Queue empty.**")
        return

    track = queues[chat_id].popleft()
    current[chat_id] = track

    try:
        await pytgcalls.change_stream(chat_id, AudioVideoPiped(track["path"]))
        if event:
            await event.edit(f"**Now Playing:**\n`{track['title']}`")
    except Exception as e:
        if event:
            await event.edit(f"**Error playing:** `{str(e)}`")
        await play_next(chat_id, event)  # Skip failed
    finally:
        # Clean up file
        try:
            os.remove(track["path"])
        except:
            pass

@ultroid_cmd(pattern="play")
async def queue_and_play(event: Message):
    reply = event.reply_to_message
    if not reply or not (reply.audio or reply.video):
        return await event.edit("**Reply to an audio or video file!**")

    chat_id = event.chat.id
    await ensure_started()

    # Download file
    file_path = await reply.download(in_memory=False)
    if not file_path:
        return await event.edit("**Failed to download.**")

    title = (reply.audio.title or reply.audio.file_name or
             reply.video.file_name or "Unknown")

    track = {"path": file_path, "title": title}
    queues[chat_id].append(track)

    await event.edit(f"**Queued:**\n`{title}`")

    # Join VC if not connected
    if not pytgcalls.is_connected(chat_id):
        try:
            await pytgcalls.join_group_call(chat_id, AudioVideoPiped(file_path))
            current[chat_id] = track
            await event.edit(f"**Joined VC and Playing:**\n`{title}`")
            # Clean up after join (but since it's current, clean on end)
        except Exception as e:
            await event.edit(f"**Error joining VC:** `{str(e)}`")
            os.remove(file_path)
            queues[chat_id].pop()  # Remove failed
            return
    elif not current.get(chat_id):  # If connected but not playing
        await play_next(chat_id, event)

@ultroid_cmd(pattern="playlist")
async def show_queue(event: Message):
    chat_id = event.chat.id
    q = queues[chat_id]
    msg = "**Queue:**\n"
    if current.get(chat_id):
        msg += f"▶️ Current: {current[chat_id]['title']}\n"
    if q:
        for i, track in enumerate(q, 1):
            msg += f"{i}. {track['title']}\n"
    else:
        msg += "Empty."
    await event.edit(msg)

@ultroid_cmd(pattern="skip")
async def skip_current(event: Message):
    chat_id = event.chat.id
    if not current.get(chat_id):
        return await event.edit("**Nothing playing.**")

    # Clean up current file
    try:
        os.remove(current[chat_id]["path"])
    except:
        pass

    current.pop(chat_id, None)

    # Stop current stream
    await pytgcalls.change_stream(chat_id, None)  # Pause

    await play_next(chat_id, event)
    await event.edit("**Skipped.**")

@ultroid_cmd(pattern="stop")
async def stop_vc(event: Message):
    chat_id = event.chat.id
    if pytgcalls.is_connected(chat_id):
        await pytgcalls.leave_group_call(chat_id)

    # Clear queue and current
    for track in list(queues[chat_id]):
        try:
            os.remove(track["path"])
        except:
            pass
    queues[chat_id].clear()
    if current.get(chat_id):
        try:
            os.remove(current[chat_id]["path"])
        except:
            pass
        current.pop(chat_id, None)

    await event.edit("**Stopped and cleared.**")
