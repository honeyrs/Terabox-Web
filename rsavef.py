# addons/rsave.py
# < Source - t.me/testingpluginnn >
# < Made for Ultroid by @Spemgod! >
# < https://github.com/TeamUltroid/Ultroid >

"""
✘ **Save a reply chain to Saved Messages!**

• **CMD:**
>  `{i}rsave` - Reply to a message to forward its entire reply chain to Saved Messages.
>  `{i}rsave <group/channel ID or @username> <message_id>` - Save the reply chain of a specific message from a group/channel.
> Example: `{i}rsave -1002804188339 123` or `{i}rsave @channelusername 123`
"""

from . import ultroid_cmd  
import asyncio
import re

@ultroid_cmd(pattern="rsave(?: (.*))?$")
async def rsave(event):
    args = event.pattern_match.group(1)
    saved_chat = await event.client.get_entity("me")

    # Handle case where a group/channel ID and message ID are provided
    if args:
        try:
            # Split arguments to extract chat ID/username and message ID
            parts = args.split()
            if len(parts) != 2:
                await event.reply("Usage: `.rsave <group/channel ID or @username> <message_id>`")
                return
            chat_id, msg_id = parts
            # Convert chat_id to int if it's a numeric ID (e.g., -1002804188339)
            try:
                chat_id = int(chat_id) if chat_id.startswith('-') else f"@{chat_id.lstrip('@')}"
            except ValueError:
                chat_id = f"@{chat_id.lstrip('@')}"  # Ensure @ for usernames
            msg_id = int(msg_id)
            target = await event.client.get_messages(chat_id, ids=msg_id)
            if not target:
                await event.reply(f"No message found with ID {msg_id} in {chat_id}.")
                return
        except Exception as e:
            await event.reply(f"Error fetching message: {str(e)}")
            return
    else:
        # Original reply-based functionality
        target = await event.get_reply_message()
        if not target:
            await event.reply("Reply to a message or provide a group/channel ID and message ID (e.g., `.rsave -1002804188339 123`).")
            return

    # Build the reply chain
    chain = []
    current = target
    while current:
        chain.append(current)
        replied = await current.get_reply_message()
        if replied:
            current = replied
        else:
            break

    if not chain:
        await event.reply("No chain found.")
        return

    status_msg = await event.reply(f"Saving {len(chain)} messages from chain...")
    if not status_msg:
        await event.client.send_message("me", f"Failed to send status message in chat {event.chat_id}. Saving {len(chain)} messages...")
        return

    saved_ids = []
    for msg in chain:
        try:
            saved = await event.client.forward_messages(saved_chat, msg, silent=True)
            saved_ids.append(saved.id)
        except Exception as e:
            await status_msg.edit(f"Error saving: {str(e)}")
            return

    # Edit status message and schedule auto-delete after 5 seconds
    await status_msg.edit(f"Saved chain to Saved Messages! Message IDs: {', '.join(map(str, saved_ids))}")
    await asyncio.sleep(5)
    try:
        await status_msg.delete()
    except Exception as e:
        await event.client.send_message("me", f"Failed to auto-delete status message: {str(e)}")
