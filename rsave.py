# addons/rsave.py
# < Source - t.me/testingpluginnn >
# < Made for Ultroid by @Spemgod! >
# < https://github.com/TeamUltroid/Ultroid >

"""
✘ **Save a reply chain to a specified chat or Saved Messages!**

• **CMD:**
>  `{i}rsave` - Reply to a message to forward its entire reply chain to Saved Messages.
>  `{i}rsave <group/channel ID or @username>` - Reply to a message to forward its reply chain to the specified chat.
> Example: `{i}rsave -1003138571490` or `{i}rsave @channelusername`
"""

from pyUltroid.utils import ultroid_cmd  # Absolute import
import asyncio

@ultroid_cmd(pattern="rsave(?: (.*))?$")
async def rsave(event):
    args = event.pattern_match.group(1)
    
    # Get the target chat (default to Saved Messages if no args)
    if args:
        try:
            # Handle chat ID or username
            chat_id = args.strip()
            target_chat = await event.client.get_entity(int(chat_id) if chat_id.startswith('-') else chat_id)
        except Exception as e:
            await event.reply(f"Error accessing chat {chat_id}: {str(e)}")
            return
    else:
        target_chat = await event.client.get_entity("me")

    # Get the replied message
    target = await event.get_reply_message()
    if not target:
        await event.reply("Reply to a message to rsave its chain!")
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

    status_msg = await event.reply(f"Saving {len(chain)} messages to chat {target_chat.id if args else 'Saved Messages'}...")
    if not status_msg:
        await event.client.send_message("me", f"Failed to send status message in chat {event.chat_id}. Saving {len(chain)} messages...")
        return

    saved_ids = []
    for msg in chain:
        try:
            saved = await event.client.forward_messages(target_chat, msg, silent=True)
            saved_ids.append(saved.id)
        except Exception as e:
            await status_msg.edit(f"Error saving: {str(e)}")
            return

    # Edit status message and schedule auto-delete after 5 seconds
    await status_msg.edit(f"Saved chain to chat {target_chat.id if args else 'Saved Messages'}! Message IDs: {', '.join(map(str, saved_ids))}")
    await asyncio.sleep(5)
    try:
        await status_msg.delete()
    except Exception as e:
        await event.client.send_message("me", f"Failed to auto-delete status message: {str(e)}")
