# addons/reminder.py
# Enhanced Reminder Plugin for Ultroid
# Supports reply-to-message reminders + auto-delete old reminders

"""
✘ **Smart Reminder Plugin**

• **Commands:**
>  `{i}reminder <minutes>` - Reply to a message → reminds by quoting it after X minutes.
>  `{i}reminder <minutes> <text>` - Without reply → uses your text.
>  Example: Reply to a message + `{i}reminder 10`
>           Or: `{i}reminder 5 Buy groceries`

>  `{i}reminder off` - Cancel pending reminder in this chat.

• Old reminder messages are automatically deleted when a new one is sent.
"""

from . import ultroid_cmd
import asyncio

# Store active reminders: {chat_id: {"task": task, "last_msg_id": int or None}}
active_reminders = {}

@ultroid_cmd(pattern="reminder(?: (.*))?$")
async def reminder_cmd(event):
    chat_id = event.chat_id
    args = event.pattern_match.group(1)

    # Cancel command
    if args and args.strip().lower() == "off":
        if chat_id in active_reminders:
            active_reminders[chat_id]["task"].cancel()
            del active_reminders[chat_id]
            await event.edit("**Reminder cancelled.**")
            await asyncio.sleep(3)
            await event.delete()
        else:
            await event.edit("**No active reminder in this chat.**")
            await asyncio.sleep(3)
            await event.delete()
        return

    # Get replied message (for quoting)
    replied = await event.get_reply_message()

    # Parse time
    if replied:
        # Case: replied to a message → time is in args
        if not args:
            await event.reply("**Please specify time in minutes when replying.**\nExample: `.reminder 10`")
            return
        time_input = args.strip()
        reminder_content = ("quote", replied)  # We'll quote the replied message
    else:
        # Case: no reply → expect time + text
        if not args:
            await event.reply(f"**Usage:**\n"
                              f"- Reply to a message + `{HNDLR}reminder <minutes>`\n"
                              f"- Or: `{HNDLR}reminder <minutes> <your text>`")
            return
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            await event.reply("**Please provide both minutes and reminder text.**")
            return
        time_input, text = parts
        reminder_content = ("text", text)

    # Validate minutes
    try:
        minutes = float(time_input)
        if minutes <= 0:
            raise ValueError
    except ValueError:
        await event.reply("**Please enter a valid positive number of minutes.**")
        return

    seconds = minutes * 60

    # Cancel any existing reminder
    if chat_id in active_reminders:
        active_reminders[chat_id]["task"].cancel()

    # Confirm reminder set
    if reminder_content[0] == "quote":
        await event.edit(f"**⏰ Reminder set for {minutes:.1f} minute(s)!**\n"
                         f"I'll quote the replied message.")
    else:
        await event.edit(f"**⏰ Reminder set for {minutes:.1f} minute(s)!**\n"
                         f"Reminder: `{reminder_content[1]}`")

    # Background task
    async def reminder_task():
        await asyncio.sleep(seconds)
        try:
            # Delete previous reminder message if exists
            if chat_id in active_reminders and active_reminders[chat_id].get("last_msg_id"):
                try:
                    await event.client.delete_messages(chat_id, active_reminders[chat_id]["last_msg_id"])
                except Exception:
                    pass  # Already deleted or no permission

            # Send new reminder
            if reminder_content[0] == "quote":
                sent = await replied.forward_to(chat_id)
                await sent.reply("**⏰ Reminder!** (set {:.1f} min ago)".format(minutes))
            else:
                sent = await event.client.send_message(
                    chat_id,
                    f"**⏰ Reminder!** (set {minutes:.1f} min ago)\n\n{reminder_content[1]}"
                )

            # Store new message ID for future deletion
            if chat_id in active_reminders:
                active_reminders[chat_id]["last_msg_id"] = sent.id

        except Exception as e:
            await event.client.send_message("me", f"Reminder failed in chat {chat_id}: {str(e)}")
        finally:
            # Clean up task reference (keep last_msg_id for deletion next time)
            if chat_id in active_reminders:
                active_reminders[chat_id].pop("task", None)

    # Start task
    task = asyncio.create_task(reminder_task())
    active_reminders[chat_id] = {"task": task, "last_msg_id": None}

    # Auto-delete the "reminder set" message after 10 seconds
    await asyncio.sleep(10)
    try:
        await event.delete()
    except Exception:
        pass
