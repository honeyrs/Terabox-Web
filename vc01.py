"""
VC Player – addons version
Commands:
  .play      → queue & play (reply to audio/video/document)
  .playlist  → show queue + current track
  .skip      → skip current
  .stop      → leave VC + clear everything
"""

import os
from collections import defaultdict, deque
from pyrogram.types import Message
from . import ultroid_cmd, vcClient, getLogger  # ← Fixed: getLogger (capital L)

log = getLogger(__name__)  # ← Use getLogger

# ----------------------------------------------------------------------
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, Update

# ----------------------------------------------------------------------
# Global objects
pytg = PyTgCalls(vcClient)  # ← vcClient (userbot for VC)
queues: defaultdict[int, deque] = defaultdict(deque)
current: dict[int, dict] = {}

# ----------------------------------------------------------------------
async def ensure_started():
    """Start py‑tgcalls only once."""
    if not pytg.is_running:
        await pytg.start()

# ----------------------------------------------------------------------
@pytg.on_stream_end()
async def _stream_ended(_: PyTgCalls, update: Update):
    """Auto‑play next track when the current one ends."""
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

    try:
        await pytg.change_stream(chat_id, AudioPiped(track["path"]))
        if msg:
            await msg.edit(f"**Now playing:** `{track['title']}`")
    except Exception as e:
        log.error(f"VC play error [{chat_id}]: {e}")
        await _play_next(chat_id, msg)  # skip broken file
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
        return await event.edit("**Reply to an audio, video, or document file!**")

    await ensure_started()
    chat_id = event.chat.id

    # Download file
    path = await reply.download(in_memory=False)
    if not path:
        return await event.edit("**Download failed.**")

    # Get title
    title = (
        reply.audio.title or
        reply.audio.file_name or
        reply.video.file_name or
        reply.document.file_name or
        "Unknown Media"
    )

    track = {"path": path, "title": title}
    queues[chat_id].append(track)
    await event.edit(f"**Queued:** `{title}`")

    # Join VC if not already connected
    if not await pytg.is_connected(chat_id):
        try:
            await pytg.join_group_call(chat_id, AudioPiped(path))
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
        # VC connected, but no current track → start playback
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
        return await event.edit("**Nothing is playing.**")

    try:
        os.remove(current[chat_id]["path"])
    except Exception:
        pass
    current.pop(chat_id, None)

    await pytg.change_stream(chat_id, None)  # Stop current stream
    await _play_next(chat_id, event)
    await event.edit("**Skipped.**")

# ----------------------------------------------------------------------
@ultroid_cmd(pattern="stop")
async def stop_cmd(event: Message):
    chat_id = event.chat.id

    if await pytg.is_connected(chat_id):
        await pytg.leave_group_call(chat_id)

    # Clear queue
    for t in list(queues[chat_id]):
        try:
            os.remove(t["path"])
        except Exception:
            pass
    queues[chat_id].clear()

    # Clear current
    if chat_id in current:
        try:
            os.remove(current[chat_id]["path"])
        except Exception:
            pass
        current.pop(chat_id, None)

    await event.edit("**Stopped & cleared.**")
