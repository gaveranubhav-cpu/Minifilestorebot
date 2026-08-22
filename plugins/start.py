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

        # 🔒 DUAL ACCESS CHECK SYSTEM (Strict Mode)
        link_data = None
        
        # 1. अगर लिंक lock_ token के रूप में आया है
        if base64_string.startswith("lock_"):
            token = base64_string.split("_", 1)[1]
            link_data = await db.get_access_link(token)
            if not link_data:
                return await message.reply_text("<b>❌ अमान्य या एक्सपायर हो चुका लिंक!</b>")
        # 2. अगर यूजर ने सीधे Original Base64 Link (Single ya Batch) पर क्लिक किया
        else:
            link_data = await db.get_access_by_data(base64_string)

        # 🛑 अगर लिंक Protected List में मौजूद है, तो User Access की जाँच करें
        if link_data:
            allowed_users = link_data.get("allowed_users", [])
            
            # ⛔ अगर यूजर Allowed List में नहीं है तो मना कर दें
            if user_id not in allowed_users:
                return await message.reply_text(
                    "<b>⛔ Access Denied!</b>\n\n"
                    "आपके पास इस स्टोरी का एक्सेस नहीं है। एक्सेस पाने के लिए पहले पेमेंट पूरा करें!",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🛍️ Check out our Mini App to buy Story", url=MINI_APP_URL)]]
                    )
                )
            
            # Approved यूजर के लिए ओरिजिनल फाइल डेटा सेट करें
            base64_string = link_data.get("base64_data", base64_string)

        # 🔓 अगर फाइल Restricted नहीं है, या यूजर Approved है तो मैसेज डिकोड करें
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

        temp_msg = await message.reply("<b>Please wait...</b>")
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await message.reply_text("Something went wrong!")
            print(f"Error getting messages: {e}")
            return
        finally:
            await temp_msg.delete()
 
        codeflix_msgs = []
        for msg in messages:
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

        if FILE_AUTO_DELETE > 0:
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

# 👑 ADMIN COMMAND: किसी भी लिंक के लिए कितने भी User IDs को एक्सेस दें
@Bot.on_message(filters.command('grantlink') & filters.private & admin)
async def grant_link_command(client: Client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text(
            "<b>Usage:</b> `/grantlink <user_id_1> <user_id_2> ... <base64_string_or_link>`\n\n"
            "<i>Example:</i> `/grantlink 123456789 987654321 Batch_123`"
        )
    
    try:
        args = message.command[1:]
        raw_input = args[-1]
        user_ids = [int(uid) for uid in args[:-1]]

        base64_data = raw_input.split("start=")[1] if "start=" in raw_input else raw_input
        token = str(uuid.uuid4())[:8]

        await db.save_access_link(token, user_ids, base64_data)
        final_link = f"https://t.me/{client.username}?start=lock_{token}"

        await message.reply_text(
            f"<b>✅ Restricted Link Created!</b>\n\n"
            f"<b>Allowed Users:</b> <code>{user_ids}</code>\n"
            f"<b>Protected Link:</b> <code>{final_link}</code>"
        )
    except Exception as e:
        await message.reply_text(f"<b>Error:</b> {e}")
