# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.
#

import asyncio
import os
import random
import sys
import time
import uuid
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from bot import Bot
from config import *
from helper_func import *
from database.database import *

BAN_SUPPORT = f"{BAN_SUPPORT}"
MINI_APP_URL = "http://t.me/storysellerbyACbot/Store"

# 🛑 ग्लोबली ट्रैक करने के लिए कि किस यूजर ने Cancel दबाया है
CANCEL_PROCESS = {}

@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id

    # Add user if not already present
    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
        except:
            pass

    # Check if user is banned
    banned_users = await db.get_ban_users()
    if user_id in banned_users:
        return await message.reply_text(
            "<b>⛔️ You are Bᴀɴɴᴇᴅ from using this bot.</b>\n\n"
            "<i>Contact support if you think this is a mistake.</i>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Contact Support", url=BAN_SUPPORT)]]
            )
        )
        
    # ✅ Check Force Subscription
    if not await is_subscribed(client, user_id):
        return await not_joined(client, message)

    # File auto-delete time in seconds
    FILE_AUTO_DELETE = await db.get_del_timer()

    # Handle normal message flow
    text = message.text
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return

        # 🔒 MANDATORY ACCESS CHECK
        has_access = await db.check_access(base64_string, user_id)

        # ⛔ अगर यूजर को इस लिंक का एक्सेस नहीं है
        if not has_access:
            return await message.reply_text(
                "<b>⛔ Access Denied!</b>\n\n"
                "आपके पास इस स्टोरी का एक्सेस नहीं है। एक्सेस पाने के लिए पहले हमारी Mini App से Buy करें!",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🛍️ Check out our Mini App to buy Story", url=MINI_APP_URL)]]
                )
            )

        # 🔓 अगर यूजर Allowed लिस्ट में है तो मैसेज निकालें
        try:
            string = await decode(base64_string)
        except Exception as e:
            return await message.reply_text("<b>❌ अमान्य या करप्ट लिंक!</b>")

        argument = string.split("-")

        ids = []
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                print(f"Error decoding IDs: {e}")
                return

        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except Exception as e:
                print(f"Error decoding ID: {e}")
                return

        # 🔘 Cancel & Buy Premium Buttons के साथ "Please wait..." मैसेज
        wait_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✖️ Cancel Process", callback_data=f"cancel_send_{user_id}")],
            [InlineKeyboardButton("🛍️ Buy Premium", url=MINI_APP_URL)]
        ])
        
        CANCEL_PROCESS[user_id] = False
        temp_msg = await message.reply("<b>Please wait... Processing your files... ⏳</b>", reply_markup=wait_markup)
        
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await temp_msg.delete()
            await message.reply_text("Something went wrong!")
            print(f"Error getting messages: {e}")
            return

        codeflix_msgs = []
        is_cancelled = False

        for msg in messages:
            # 🛑 अगर यूजर ने Cancel बटन दबा दिया है
            if CANCEL_PROCESS.get(user_id, False):
                is_cancelled = True
                break

            caption = (CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, 
                                             filename=msg.document.file_name) if bool(CUSTOM_CAPTION) and bool(msg.document)
                       else ("" if not msg.caption else msg.caption.html))
            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None
            try:
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT
                )
                await asyncio.sleep(1)
                codeflix_msgs.append(copied_msg)
            except Exception as e:
                print(f"Failed to send message: {e}")

        # ✅ सब फ़ाइलें भेजने के बाद ही `Please wait...` डिलीट होगा
        try:
            await temp_msg.delete()
        except Exception:
            pass

        if is_cancelled:
            CANCEL_PROCESS.pop(user_id, None)
            return await message.reply_text("<b>❌ प्रोसेस को आपकी तरफ से कैंसिल कर दिया गया।</b>")

        CANCEL_PROCESS.pop(user_id, None)

        if FILE_AUTO_DELETE > 0 and codeflix_msgs:
            notification_msg = await message.reply(
                f"<b>Tʜɪs Fɪʟᴇ ᴡɪʟʟ ʙᴇ Dᴇʟᴇᴛᴇᴅ ɪɴ  {get_exp_time(FILE_AUTO_DELETE)}. Pʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ʙᴇғᴏʀᴇ ɪᴛ ɢᴇᴛs Dᴇʟᴇᴛᴇᴅ.</b>"
            )
            reload_url = (
                f"https://t.me/{client.username}?start={message.command[1]}"
                if message.command and len(message.command) > 1
                else None
            )
            asyncio.create_task(
                schedule_auto_delete(client, codeflix_msgs, notification_msg, FILE_AUTO_DELETE, reload_url)
            )
    else:
        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🛍️ Check out our Mini App to buy Story", url=MINI_APP_URL)],
                [
                    InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data = "about"),
                    InlineKeyboardButton('ʜᴇʟᴘ •', callback_data = "help")
                ]
            ]
        )
        await message.reply_photo(
            photo=START_PIC,
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
            message_effect_id=5104841245755180586)
        
        return

# 🔘 CANCEL BUTTON CALLBACK HANDLER
@Bot.on_callback_query(filters.regex(r"^cancel_send_"))
async def cancel_callback_handler(client: Client, query: CallbackQuery):
    target_user_id = int(query.data.split("_")[2])
    
    if query.from_user.id != target_user_id:
        return await query.answer("<b>❌ यह कैंसिल बटन आपके लिए नहीं है!</b>", show_alert=True)
    
    CANCEL_PROCESS[target_user_id] = True
    await query.answer("<b>प्रोसेस कैंसिल की जा रही है...</b>", show_alert=True)

# 👑 ADMIN COMMAND: यूजर्स को लिंक का एक्सेस दें
@Bot.on_message(filters.command('grantlink') & filters.private & admin)
async def grant_link_command(client: Client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text(
            "<b>Usage:</b> `/grantlink <user_id_1> <user_id_2> ... <link_or_base64>`\n\n"
            "<i>Example:</i> `/grantlink 123456789 987654321 https://t.me/bot?start=Batch_123`"
        )
    
    try:
        args = message.command[1:]
        raw_input = args[-1]
        user_ids = [int(uid) for uid in args[:-1]]

        base64_data = raw_input.split("start=")[1] if "start=" in raw_input else raw_input

        await db.grant_user_access(base64_data, user_ids)

        await message.reply_text(
            f"<b>✅ Access Granted Successfully!</b>\n\n"
            f"<b>Allowed Users:</b> <code>{user_ids}</code>\n"
            f"<b>Target Link Payload:</b> <code>{base64_data}</code>"
        )
    except Exception as e:
        await message.reply_text(f"<b>Error:</b> {e}")
