# /root/TeamUltroid/addons/save (1).py
from pyUltroid.fns.tools import ultroid_bot as ultroid_cmd  # Alias ultroid_bot to ultroid_cmd
from pyUltroid.fns.helper import eod  # Ensure eod is imported correctly

async def get_reply_chain(message, client):
    """Recursively collect all messages in the reply chain."""
    chain = []
    current_message = message
    
    while current_message and current_message.reply_to_message_id:
        chain.append(current_message)
        try:
            current_message = await client.get_messages(
                current_message.chat_id,
                current_message.reply_to_message_id
            )
        except Exception as error:
            print(f"Error fetching reply: {error}")
            break
    
    if current_message and current_message not in chain:
        chain.append(current_message)
    
    return chain

@ultroid_cmd(pattern="rsave", fullsudo=True)
async def save_reply_chain(e):
    """Forwards the replied message and its reply chain to Saved Messages."""
    if not e.reply_to:
        return await eod(e, "`Please reply to a message to save it and its reply chain to Saved Messages.`")
    
    try:
        replied_message = await e.get_reply_message()
        reply_chain = await get_reply_chain(replied_message, e.client)
        
        if not reply_chain:
            return await eod(e, "`No messages found in the reply chain.`")
        
        me = await e.client.get_me()
        for msg in reversed(reply_chain):
            await e.client.forward_messages(
                entity=me,
                messages=msg
            )
        
        await eod(e, f"`Successfully forwarded {len(reply_chain)} message(s) to Saved Messages!`")
    
    except Exception as error:
        await eod(e, f"**Error:** `{error}`")
