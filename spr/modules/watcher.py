import os
from pyrogram import filters
from pyrogram.types import Message
from spr import SUDOERS, arq, spr
from spr.utils.db import (
    add_chat, add_user, chat_exists, is_chat_blacklisted,
    is_nsfw_downvoted, is_nsfw_enabled, is_spam_enabled,
    is_user_blacklisted, update_spam_data, user_exists
)
from spr.utils.functions import (
    delete_nsfw_notify, delete_spam_notify, kick_user_notify
)
from spr.utils.misc import admins, get_file_id, get_file_unique_id


@spr.on_message(filters.document | filters.photo | filters.sticker |
                filters.animation | filters.video | filters.text)
async def message_watcher(_, message: Message):
    chat_id, user_id = None, None

    if message.chat.type in ["group", "supergroup"]:
        chat_id = message.chat.id
        if not chat_exists(chat_id):
            add_chat(chat_id)
        if is_chat_blacklisted(chat_id):
            return await spr.leave_chat(chat_id)

    if message.from_user and message.from_user.id:
        user_id = message.from_user.id
        if not user_exists(user_id):
            add_user(user_id)
        if is_user_blacklisted(user_id) and chat_id:
            if user_id not in await admins(chat_id):
                return await kick_user_notify(message)

    if not chat_id or not user_id:
        return

    file_id = get_file_id(message)
    file_unique_id = get_file_unique_id(message)

    if file_id and file_unique_id:
        if user_id in SUDOERS or user_id in await admins(chat_id):
            return
        if is_nsfw_downvoted(file_unique_id):
            return

        file = await spr.download_media(file_id)
        if not file:
            return

        try:
            resp = await arq.nsfw_scan(file=file)
        except Exception as e:
            os.remove(file)
            return

        os.remove(file)

        if resp.ok and hasattr(resp.result, "is_nsfw") and resp.result.is_nsfw:
            if is_nsfw_enabled(chat_id):
                return await delete_nsfw_notify(message, resp.result)

    text = message.text or message.caption
    if not text:
        return

    try:
        resp = await arq.nlp(text)
    except Exception:
        return

    if not resp.ok or not resp.result:
        return

    result = resp.result[0]
    update_spam_data(user_id, result.spam)

    if result.is_spam and is_spam_enabled(chat_id):
        if user_id not in SUDOERS and user_id not in await admins(chat_id):
            await delete_spam_notify(message, result.spam_probability)
