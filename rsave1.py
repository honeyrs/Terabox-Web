# addons/rsave.py
from pyUltroid import ultroid_cmd  # Use absolute import

@ultroid_cmd(pattern="rsave")
async def rsave(event):
    target = await event.get_reply_message()
    if not target:
        await event.reply("Reply to a message to rsave the chain!")
        return
    saved_chat = await event.client.get_entity("me")
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
    await status_msg.edit(f"Saved chain to Saved Messages! Message IDs: {', '.join(map(str, saved_ids))}")
