from os import remove

from pyrogram import filters
from pyrogram.types import Message

from spr import SUDOERS, arq, spr
from spr.utils.db import (disable_nsfw, disable_spam, enable_nsfw,
                          enable_spam, is_nsfw_enabled,
                          is_spam_enabled)
from spr.utils.misc import admins, get_file_id

__MODULE__ = "Manage"
__HELP__ = """
- **/antinsfw [ENABLE|DISABLE]** – Bật hoặc tắt tính năng phát hiện nội dung NSFW.
- **/antispam [ENABLE|DISABLE]** – Bật hoặc tắt tính năng phát hiện spam.
- **/nsfwscan** – Phân loại nội dung media để kiểm tra xem có phải NSFW không.
- **/spamscan** – Dự đoán mức độ spam của tin nhắn được phản hồi.
"""


@spr.on_message(
    filters.command("antinsfw") & ~filters.private, group=3
)
async def nsfw_toggle_func(_, message: Message):
    if len(message.command) != 2:
        return await message.reply_text(
            "Cách dùng: /antinsfw [ENABLE|DISABLE]"
        )
    if message.from_user:
        user = message.from_user
        chat_id = message.chat.id
        if user.id not in SUDOERS and user.id not in (
            await admins(chat_id)
        ):
            return await message.reply_text(
                "Bạn không có đủ quyền."
            )
    status = message.text.split(None, 1)[1].strip()
    status = status.lower()
    chat_id = message.chat.id
    if status == "enable":
        if is_nsfw_enabled(chat_id):
            return await message.reply("Đã bật.")
        enable_nsfw(chat_id)
        await message.reply_text("Đã bật tính năng phát hiện NSFW.")
    elif status == "disable":
        if not is_nsfw_enabled(chat_id):
            return await message.reply("Đã tắt.")
        disable_nsfw(chat_id)
        await message.reply_text("Đã tắt tính năng phát hiện NSFW.")
    else:
        await message.reply_text(
            "Sai lệnh, Dùng /antinsfw [ENABLE|DISABLE]"
        )


@spr.on_message(
    filters.command("antispam") & ~filters.private, group=3
)
async def spam_toggle_func(_, message: Message):
    if len(message.command) != 2:
        return await message.reply_text(
            "Cách dùng: /antispam [ENABLE|DISABLE]"
        )
    if message.from_user:
        user = message.from_user
        chat_id = message.chat.id
        if user.id not in SUDOERS and user.id not in (
            await admins(chat_id)
        ):
            return await message.reply_text(
                "Bạn không có đủ quyền."
            )
    status = message.text.split(None, 1)[1].strip()
    status = status.lower()
    chat_id = message.chat.id
    if status == "enable":
        if is_spam_enabled(chat_id):
            return await message.reply("Đã bật.")
        enable_spam(chat_id)
        await message.reply_text("Đã bật tính năng phát hiện spam.")
    elif status == "disable":
        if not is_spam_enabled(chat_id):
            return await message.reply("Đã bật.")
        disable_spam(chat_id)
        await message.reply_text("Đã tắt tính năng phát hiện spam.")
    else:
        await message.reply_text(
            "Sai lệnh, Dùng /antispam [ENABLE|DISABLE]"
        )


@spr.on_message(filters.command("nsfwscan"), group=3)
async def nsfw_scan_command(_, message: Message):
    err = "Trả lời bằng hình ảnh/tài liệu/nhãn dán/hoạt ảnh để quét nó."
    if not message.reply_to_message:
        await message.reply_text(err)
        return
    reply = message.reply_to_message
    if (
        not reply.document
        and not reply.photo
        and not reply.sticker
        and not reply.animation
        and not reply.video
    ):
        await message.reply_text(err)
        return
    m = await message.reply_text("Đang quét")
    file_id = get_file_id(reply)
    if not file_id:
        return await m.edit("Có gì đó không ổn.")
    file = await spr.download_media(file_id)
    try:
        results = await arq.nsfw_scan(file=file)
    except Exception as e:
        return await m.edit(str(e))
    remove(file)
    if not results.ok:
        return await m.edit(results.result)
    results = results.result
    await m.edit(
        f"""
**Trung tính:** `{results.neutral} %`
**Porn:** `{results.porn} %`
**Hentai:** `{results.hentai} %`
**Sexy:** `{results.sexy} %`
**Hình vẽ:** `{results.drawings} %`
**NSFW:** `{results.is_nsfw}`
"""
    )


@spr.on_message(filters.command("spamscan"), group=3)
async def scanNLP(_, message: Message):
    if not message.reply_to_message:
        return await message.reply("Trả lời một tin nhắn để quét nó.")
    r = message.reply_to_message
    text = r.text or r.caption
    if not text:
        return await message.reply("Không thể quét")
    data = await arq.nlp(text)
    data = data.result[0]
    msg = f"""
**Có phải spam:** {data.is_spam}  
**Xác suất spam:** {data.spam_probability} %  
**Spam:** {data.spam}  
**Không phải spam (Ham):** {data.ham}  
**Ngôn từ tục tĩu:** {data.profanity}
"""
    await message.reply(msg, quote=True)
