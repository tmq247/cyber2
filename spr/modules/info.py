from time import ctime

from pyrogram import filters
from pyrogram.types import (InlineQuery, InlineQueryResultArticle,
                            InputTextMessageContent, Message)

from spr import SUDOERS, spr
from spr.utils.db import (add_chat, add_user, chat_exists,
                          get_blacklist_event, get_nsfw_count,
                          get_reputation, get_user_trust,
                          is_chat_blacklisted, is_user_blacklisted,
                          user_exists)

__MODULE__ = "Info"
__HELP__ = """
**Get Info About A Chat Or User**

/info [CHAT_ID/Username|USER_ID/Username]

"""


async def get_user_info(user):
    try:
        user = await spr.get_users(user)
    except Exception:
        return
    if not user_exists(user.id):
        add_user(user.id)
    trust = get_user_trust(user.id)
    blacklisted = is_user_blacklisted(user.id)
    reason = None
    if blacklisted:
        reason, time = get_blacklist_event(user.id)
    data = f"""
**Thông tin người dùng:**  
- **ID:** {user.id}  
- **Trung tâm dữ liệu (DC):** {user.dc_id}  
- **Tên người dùng:** {user.username}  
- **Nhắc đến:** {user.mention("Liên kết")}  

**Trạng thái:**  
- **Là Sudo:** {user.id in SUDOERS}  
- **Độ tin cậy:** {trust}  
- **Người gửi spam:** {True if trust < 50 else False}  
- **Danh tiếng:** {get_reputation(user.id)}  
- **Số lần đăng NSFW:** {get_nsfw_count(user.id)}  
- **Có khả năng là spammer:** {True if trust < 70 else False}  
- **Bị đưa vào danh sách đen:** {blacklisted}  
"""
    data += (
        f"**Lý do danh sách đen:** {reason} | {ctime(time)}"
        if reason
        else ""
    )
    return data


async def get_chat_info(chat):
    try:
        chat = await spr.get_chat(chat)
    except Exception:
        return
    if not chat_exists(chat.id):
        add_chat(chat.id)
    blacklisted = is_chat_blacklisted(chat.id)
    reason = None
    if blacklisted:
        reason, time = get_blacklist_event(chat.id)
    data = f"""
**Thông tin cuộc trò chuyện:**  
- **ID:** {chat.id}  
- **Tên người dùng:** {chat.username}  
- **Loại:** {chat.type}  
- **Số thành viên:** {chat.members_count}  
- **Lừa đảo:** {chat.is_scam}  
- **Bị hạn chế:** {chat.is_restricted}  
- **Bị đưa vào danh sách đen:** {blacklisted}  
"""
    data += (
        f"**Lý do danh sách đen:** {reason} | {ctime(time)}"
        if reason
        else ""
    )
    return data


async def get_info(entity):
    user = await get_user_info(entity)
    if user:
        return user
    chat = await get_chat_info(entity)
    return chat


@spr.on_message(filters.command("info"), group=3)
async def info_func(_, message: Message):
    if message.reply_to_message:
        reply = message.reply_to_message
        user = reply.from_user
        entity = user.id or message.chat.id
    elif len(message.command) == 1:
        user = message.from_user
        entity = user.id or message.chat.id
    elif len(message.command) == 2:
        entity = message.text.split(None, 1)[1]
    else:
        return await message.reply_text("Đọc menu trợ giúp")
    entity = await get_info(entity)
    entity = entity or "Tôi chưa thấy cuộc trò chuyện/người dùng này."
    await message.reply_text(entity)


@spr.on_inline_query()
async def inline_info_func(_, query: InlineQuery):
    query_ = query.query.strip()
    entity = await get_info(query_)
    if not entity:
        err = "Tôi chưa thấy người dùng/cuộc trò chuyện này."
        results = [
            InlineQueryResultArticle(
                err,
                input_message_content=InputTextMessageContent(err),
            )
        ]
    else:
        results = [
            InlineQueryResultArticle(
                "Found Entity",
                input_message_content=InputTextMessageContent(entity),
            )
        ]
    await query.answer(results=results, cache_time=3)
