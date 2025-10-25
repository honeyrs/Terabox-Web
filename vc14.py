"""
VC Player – addons version
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
# py-tgcalls latest API
from pytgcalls import GroupCallFactory
from pytgcalls.mtproto_client_type import MTProtoClientType
from pytgcalls.implementation.group_call_file import GroupCallFileAction

# ----------------------------------------------------------------------
# Global objects
group_call_factory = GroupCallFactory(
    vcClient, mtproto_backend=MTProtoClientType.PYROGRAM
)
queues: defaultdict[int, deque] = defaultdict(deque)
current: dict[int, dict] = {}

# ----------------------------------------------------------------------
async def _on_ended(chat_id: int, path: str):
    """Clean up ended track and play next if available."""
    try:
        os.remove(path)
    except Exception:
        pass
    current.pop(chat_id, None)
    if queues[chat_id]:
        await _play_next(chat_id)

# ----------------------------------------------------------------------
async def _play_next(chat_id: int, msg: Message | None = None):
    """Play next track in queue."""
    if not queues[chat_id]:
        return

    track = queues[chat_id].popleft()
    path = track["path"]
    title = track["title"]

    def ended_callback(gc):
        loop = asyncio.get_event_loop()
        loop.create_task(_on_ended(chat_id, path))

    group_call = group_call_factory.get_file_group_call(input_filename=path)
    group_call.set_on_action(GroupCallFileAction.PLAYOUT_ENDED, ended_callback)

    current[chat_id] = {
        "group_call": group_call,
        "title": title,
        "path": path,
    }

    await group_call.start(chat_id)
    if msg:
        await msg.edit(f"**Now playing:** `{title}`")

# ----------------------------------------------------------------------
@ultroid_cmd(pattern="play")
async def play_cmd(event: Message):
    reply = event.reply_to_message
    if not reply or not (reply.audio or reply.video or reply.document):
        return await event.edit("**Reply to an audio, video, or document file!**")

    chat_id = event.chat.id

    # Download
    path = await reply.download(in_memory=False)
    if not path:
        return await event.edit("**Download failed.**")

    # Title
    title = (
        getattr(reply.audio, "title", None)
        or getattr(reply.audio, "file_name", None)
        or getattr(reply.video, "file_name", None)
        or getattr(reply.document, "file_name", None)
        or "Unknown Media"
    )

    track = {"path": path, "title": title}
    queues[chat_id].append(track)
    await event.edit(f"**Queued:** `{title}`")

    # Start playing if not already
    if chat_id not in current:
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

    curr = current[chat_id]
    await curr["group_call"].stop()
    try:
        os.remove(curr["path"])
    except Exception:
        pass
    current.pop(chat_id, None)

    await _play_next(chat_id, event)
    await event.edit("**Skipped.**")

# ----------------------------------------------------------------------
@ultroid_cmd(pattern="stop")
async def stop_cmd(event: Message):
    chat_id = event.chat.id

    # Stop current
    if chat_id in current:
        curr = current[chat_id]
        await curr["group_call"].leave_current_group_call()
        try:
            os.remove(curr["path"])
        except Exception:
            pass
        current.pop(chat_id, None)

    # Clear queue
    for t in list(queues[chat_id]):
        try:
            os.remove(t["path"])
        except Exception:
            pass
    queues[chat_id].clear()

    await event.edit("**Stopped & cleared.**")
