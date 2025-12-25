# addons/reminder.py
# Repeating Clean Reminder Plugin for Ultroid

"""
✘ **Repeating Reminder Plugin**

• **Commands:**
>  `{i}reminder <time>` - Reply to a message → repeats quoting it every X time
>  `{i}reminder <time> <text>` - Repeats your text every X time

• **Time formats:**
>  `5` or `5m` → every 5 minutes
>  `30s` → every 30 seconds
>  `2h` → every 2 hours
>  `1.5h` → every 1.5 hours

>  `{i}reminder off` - Stop the repeating reminder in this chat

• Only the latest reminder message is kept (old one deleted automatically)
• No extra text — pure message only
"""

from . import ultroid_cmd
import asyncio
import re

# Store per chat: repeating task and last sent message ID
active_reminders = {}

def parse_time(time_str):
    """Parse time like '5', '30s', '10m', '2h' → seconds"""
    time_str = time_str.lower().strip()
    match = re.match(r'^(\d*\.?\d+)\s*(s|m|h)?$', time_str)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2) or 'm'  # default minutes
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

    # Stop repeating reminder
    if args and args.strip().lower() == "off":
        if chat_id in active_reminders:
            active_reminders[chat_id]["task"].cancel()
            del active_reminders[chat_id]
            await event.edit("**Repeating reminder stopped.**")
            await asyncio.sleep(3)
            await event.delete()
        else:
            await event.edit("**No active repeating reminder in this chat.**")
            await asyncio.sleep(3)
            await event.delete()
        return

    replied = await event.get_reply_message()

    if replied:
        if not args:
            await event.reply("**Specify interval time.**\nExamples: `.reminder 5m`, `.reminder 30s`, `.reminder 1h`")
            return
        time_input = args.strip()
        reminder_content = ("quote", replied)
    else:
        if not args:
            await event.reply("**Usage:**\n"
                              "- Reply + `.reminder <time>`\n"
                              "- Or: `.reminder <time> <your message>`")
            return
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            await event.reply("**Provide time and message.**\nExample: `.reminder 10m Drink water`")
            return
        time_input, text = parts
        reminder_content = ("text", text)

    # Parse interval
    seconds = parse_time(time_input)
    if seconds is None or seconds <= 0:
        await event.reply("**Invalid time.** Use: `5`, `30s`, `10m`, `2h`, `1.5h`")
        return

    # Stop any existing reminder
    if chat_id in active_reminders:
        active_reminders[chat_id]["task"].cancel()

    # Confirm
    mins = seconds / 60
    hrs = seconds / 3600
    if hrs >= 1:
        display = f"{hrs:.2f} hour(s)" if hrs > 1 else "1 hour"
    elif mins >= 1:
        display = f"{mins:.1f} minute(s)" if mins > 1 else "1 minute"
    else:
        display = f"{seconds:.1f} second(s)"

    await event.edit(f"**Repeating reminder set — every {display}.**\nUse `.reminder off` to stop.")

    # Repeating task
    async def repeat_reminder():
        while True:
            await asyncio.sleep(seconds)
            try:
                # Delete previous reminder message
                if chat_id in active_reminders and active_reminders[chat_id].get("last_msg_id"):
                    try:
                        await event.client.delete_messages(chat_id, active_reminders[chat_id]["last_msg_id"])
                    except Exception:
                        pass

                # Send new clean reminder
                if reminder_content[0] == "quote":
                    sent = await replied.forward_to(chat_id)
                else:
                    sent = await event.client.send_message(chat_id, reminder_content[1])

                # Update last message ID
                if chat_id in active_reminders:
                    active_reminders[chat_id]["last_msg_id"] = sent.id

            except asyncio.CancelledError:
                break  # Task cancelled
            except Exception as e:
                await event.client.send_message("me", f"Repeating reminder failed in {chat_id}: {str(e)}")
                break

    # Start repeating
    task = asyncio.create_task(repeat_reminder())
    active_reminders[chat_id] = {"task": task, "last_msg_id": None}

    # Auto-delete confirmation
    await asyncio.sleep(8)
    try:
        await event.delete()
    except Exception:
        pass
