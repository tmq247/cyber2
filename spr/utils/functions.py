from time import ctime

from pyrogram.errors import (ChatAdminRequired, ChatWriteForbidden,
                             UserAdminInvalid)
from pyrogram.types import Message

from spr import NSFW_LOG_CHANNEL, SPAM_LOG_CHANNEL, spr
from spr.core import ikb
from spr.utils.db import (get_blacklist_event, get_nsfw_count,
                          get_reputation, get_user_trust,
                          increment_nsfw_count, is_user_blacklisted)


async def get_user_info(message):
    user = message.from_user
    trust = get_user_trust(user.id)
    user_ = f"{('@' + user.username) if user.username else user.mention} [`{user.id}`]"
    blacklisted = is_user_blacklisted(user.id)
    reason = None
    if blacklisted:
        reason, time = get_blacklist_event(user.id)
    data = f"""
**Người dùng:**  
   **Tên người dùng:** {user_}  
   **Độ tin cậy:** {trust}  
   **Có phải spammer:** {True if trust < 50 else False}  
   **Danh tiếng:** {get_reputation(user.id)}  
   **Số lần gửi NSFW:** {get_nsfw_count(user.id)}  
   **Có thể là spammer:** {True if trust < 70 else False}  
   **Bị đưa vào danh sách đen:** {is_user_blacklisted(user.id)}  
"""
    data += (
        f"    **Lý do bị đưa vào danh sách đen:** {reason} | {ctime(time)}"
        if reason
        else ""
    )
    return data


async def delete_get_info(message: Message):
    try:
        await message.delete()
    except (ChatAdminRequired, UserAdminInvalid):
        try:
            return await message.reply_text(
                "Tôi không đủ quyền để xóa tin nhắn này "
                + "tin nhắn bị đánh dấu là Spam."
            )
        except ChatWriteForbidden:
            return await spr.leave_chat(message.chat.id)
    return await get_user_info(message)


async def delete_nsfw_notify(
    message: Message,
    result,
):
    await message.copy(
        NSFW_LOG_CHANNEL,
        reply_markup=ikb(
            {"Đúng": "upvote_nsfw", "Sai": "downvote_nsfw"}
        ),
    )
    info = await delete_get_info(message)
    if not info:
        return
    msg = f"""
🚨 **Cảnh báo NSFW**  🚔
{info}
**Dự đoán:**
    **An toàn:** `{result.neutral} %`
    **Porn:** `{result.porn} %`
    **Adult:** `{result.sexy} %`
    **Hentai:** `{result.hentai} %`
    **Hình vẽ:** `{result.drawings} %`
"""
    await spr.send_message(message.chat.id, text=msg)
    increment_nsfw_count(message.from_user.id)


async def delete_spam_notify(
    message: Message,
    spam_probability: float,
):
    info = await delete_get_info(message)
    if not info:
        return
    msg = f"""
🚨 **Cảnh báo SPAM**  🚔
{info}
**Xác xuất SPAM:** {spam_probability} %

__Tin nhắn đã bị xóa__
"""
    content = message.text or message.caption
    content = content[:400] + "..."
    report = f"""
**Phát hiện SPAM**
{info}
**Nội dung:**
{content}
    """

    keyb = ikb(
        {
            "Đúng (0)": "upvote_spam",
            "Sai (0)": "downvote_spam",
            "Chat": "https://t.me/" + (message.chat.username or "SpamProtectionLog/93"),
        },
        2
    )
    m = await spr.send_message(
        SPAM_LOG_CHANNEL,
        report,
        reply_markup=keyb,
        disable_web_page_preview=True,
    )

    keyb = ikb({"Xem tin nhắn": m.link})
    await spr.send_message(
        message.chat.id, text=msg, reply_markup=keyb
    )


async def kick_user_notify(message: Message):
    try:
        await spr.ban_chat_member(
            message.chat.id, message.from_user.id
        )
    except (ChatAdminRequired, UserAdminInvalid):
        try:
            return await message.reply_text(
                "Tôi không có đủ quyền để ban "
                + "người dùng này đã bị đưa vào danh sách đen và bị đánh dấu là spammer."
            )
        except ChatWriteForbidden:
            return await spr.leave_chat(message.chat.id)
    info = await get_user_info(message)
    msg = f"""
🚨 **Cảnh báo SPAMMER**  🚔
{info}

__Người này đã bị ban__
"""
    await spr.send_message(message.chat.id, msg)
