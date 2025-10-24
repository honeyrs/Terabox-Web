from telethon import events
from telethon.tl.types import Message
from ultroid.utils import udB, admin_cmd, edit_delete, reply_id

SAVED_MSGS = udB.get_key("SAVED_MSGS") or "me"

@ultroid_cmd(pattern="savethread")
async def savethread(event):
    if not event.is_reply:
        await edit_delete(event, "__Reply to a message to save its thread!__")
        return
    reply_to_id = await reply_id(event)
    messages_to_save = [await event.get_reply_message()]
    async for reply in event.client.iter_messages(event.chat_id, reply_to=reply_to_id):
        messages_to_save.append(reply)
    
    if len(messages_to_save) == 1:
        await edit_delete(event, "__No replies found in this thread.__")
        return
    
    messages_to_save.reverse()  # Chronological order: original first, then replies
    await event.edit(f"Saving {len(messages_to_save)} messages from thread...")
    
    try:
        for msg in messages_to_save:
            await event.client.forward_messages(SAVED_MSGS, msg)
        await edit_delete(event, f"__Thread saved to Saved Messages! ({len(messages_to_save)} msgs)__")
    except Exception as e:
        await edit_delete(event, f"__Error saving thread: {str(e)}__")

CMD_HELP.update(
    {
        "savethread": f"**Plugin for:** \
        \n\n • **`.savethread`** to save a message and its replies (thread) to Saved Messages."
    }
)
