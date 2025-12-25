# addons/reminder.py
# Clean & Smart Reminder Plugin for Ultroid

"""
✘ **Reminder Plugin**

• **Commands:**
>  `{i}reminder <time> [text]` - Set reminder with text (no reply needed)
>  Reply + `{i}reminder <time>` - Remind by quoting the replied message

• **Time formats:**
>  `5` or `5m` → 5 minutes  
>  `30s` → 30 seconds  
>  `2h` → 2 hours  
>  `1.5h` → 1 hour 30 minutes

>  `{i}reminder off` - Cancel active reminder in this chat

• Old reminder messages are deleted when a new one is sent.
"""

from . import ultroid_cmd
import asyncio
import re

# Store per chat: task and last sent reminder message ID
active_reminders = {}

def parse_time(time_str):
    """Parse time string like '5', '5s', '30m', '2h', '1.5h' into seconds"""
    time_str = time_str.lower().strip()
    match = re.match(r'^(\d*\.?\d+)\s*(s|m|h)?$', time_str)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2) or 'm'  # default to minutes
    if unit == 's':
        return value
    elif unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    return None

@ultroid_cmd(pattern="reminder(?: (.*))?$")
async def reminder_cmd(event):
    chat_id = event.chat_id
    args = event.pattern_match.group(1)

    # Cancel command
    if args and args.strip().lower() == "off":
        if chat_id in active_reminders:
            active_reminders[chat_id]["task"].cancel()
            del active_reminders[chat_id]
            await event.edit("**⏰ Reminder cancelled.**")
            await asyncio.sleep(3)
            await event.delete()
        else:
            await event.edit("**No active reminder in this chat.**")
            await asyncio.sleep(3)
            await event.delete()
        return

    replied = await event.get_reply_message()

    if replied:
        # Reply mode: expect only time in args
        if not args:
            await event.reply("**Please specify time.**\nExamples: `.reminder 5s`, `.reminder 10m`, `.reminder 1h`")
            return
        time_input = args.strip()
        reminder_content = ("quote", replied)
    else:
        # Text mode: expect time + text
        if not args:
            await event.reply("**Usage:**\n"
                              "- Reply to message + `.reminder <time>`\n"
                              "- Or: `.reminder <time> <your text>`")
            return
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            await event.reply("**Please provide time and reminder text.**\nExample: `.reminder 5m Buy milk`")
            return
        time_input, text = parts
        reminder_content = ("text", text)

    # Parse time
    seconds = parse_time(time_input)
    if seconds is None or seconds <= 0:
        await event.reply("**Invalid time format.**\nUse: `5`, `30s`, `10m`, `2h`, `1.5h`")
        return

    # Cancel any existing reminder
    if chat_id in active_reminders:
        active_reminders[chat_id]["task"].cancel()

    # Confirm
    mins = seconds / 60
    hrs = seconds / 3600
    if hrs >= 1:
        time_display = f"{hrs:.2f} hour(s)" if hrs != 1 else "1 hour"
    elif mins >= 1:
        time_display = f"{mins:.1f} minute(s)" if mins != 1 else "1 minute"
    else:
        time_display = f"{seconds:.1f} second(s)"

    await event.edit(f"**⏰ Reminder set for {time_display}!**")

    # Reminder task
    async def reminder_task():
        await asyncio.sleep(seconds)
        try:
            # Delete old reminder message if exists
            if chat_id in active_reminders and active_reminders[chat_id].get("last_msg_id"):
                try:
                    await event.client.delete_messages(chat_id, active_reminders[chat_id]["last_msg_id"])
                except Exception:
                    pass

            # Send new reminder
            if reminder_content[0] == "quote":
                sent = await replied.forward_to(chat_id)
                reminder_msg = await sent.reply("**⏰ Reminder!**")
            else:
                reminder_msg = await event.client.send_message(
                    chat_id,
                    f"**⏰ Reminder!**\n\n{reminder_content[1]}"
                )

            # Store new message ID
            if chat_id in active_reminders:
                active_reminders[chat_id]["last_msg_id"] = reminder_msg.id

        except Exception as e:
            await event.client.send_message("me", f"Reminder failed in chat {chat_id}: {str(e)}")
        finally:
            if chat_id in active_reminders:
                active_reminders[chat_id].pop("task", None)

    # Start task
    task = asyncio.create_task(reminder_task())
    active_reminders[chat_id] = {"task": task, "last_msg_id": None}

    # Auto-delete confirmation after 8 seconds
    await asyncio.sleep(8)
    try:
        await event.delete()
    except Exception:
        pass
