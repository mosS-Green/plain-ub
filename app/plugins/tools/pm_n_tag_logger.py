import asyncio

from pyrogram import filters
from pyrogram.enums import ChatType, MessageEntityType
from pyrogram.errors import MessageIdInvalid

from app import BOT, Config, CustomDB, Message, bot, try_

LOGGER = CustomDB("COMMON_SETTINGS")

MESSAGE_CACHE: dict[int, list[Message]] = {}

LAST_PM_LOGGED_ID = 0


async def init_task():
    tag_check = await LOGGER.find_one({"_id": "tag_logger_switch"})
    pm_check = await LOGGER.find_one({"_id": "pm_logger_switch"})
    if tag_check:
        Config.TAG_LOGGER = tag_check["value"]
    if pm_check:
        Config.PM_LOGGER = pm_check["value"]
    Config.MESSAGE_LOGGER_TASK = asyncio.create_task(runner())


@bot.add_cmd(cmd=["taglogger", "pmlogger"])
async def logger_switch(bot: BOT, message: Message):
    """
    CMD: TAGLOGGER | PMLOGGER
    INFO: Enable/Disable PM or Tag Logger.
    FLAGS: -c to check status.
    """
    text = "pm" if message.cmd == "pmlogger" else "tag"
    conf_str = f"{text.upper()}_LOGGER"
    if "-c" in message.flags:
        await message.reply(
            text=f"{text.capitalize()} Logger is enabled: <b>{getattr(Config, conf_str)}</b>!",
            del_in=8,
        )
        return
    value: bool = not getattr(Config, conf_str)
    setattr(Config, conf_str, value)
    await asyncio.gather(
        LOGGER.add_data({"_id": f"{text}_logger_switch", "value": value}),
        message.reply(
            text=f"{text.capitalize()} Logger is enabled: <b>{value}</b>!", del_in=8
        ),
        bot.log_text(
            text=f"#{text.capitalize()}Logger is enabled: <b>{value}</b>!", type="info"
        ),
    )
    Config.MESSAGE_LOGGER_TASK = asyncio.create_task(runner())


basic_filters = (
    ~filters.channel
    & ~filters.bot
    & ~filters.service
    & ~filters.chat(chats=[bot.me.id])
    & ~filters.me
)


@try_
@bot.on_message(
    filters=basic_filters
    & filters.private
    & filters.create(lambda _, __, ___: Config.PM_LOGGER),
    group=2,
)
async def pm_logger(bot: BOT, message: Message):
    cache_message(message)


tag_filter = filters.create(lambda _, __, ___: Config.TAG_LOGGER)


@try_
@bot.on_message(
    filters=(basic_filters & filters.reply & tag_filter) & ~filters.private, group=2
)
async def reply_logger(bot: BOT, message: Message):
    if (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.me.id
    ):
        cache_message(message)
    message.continue_propagation()


@try_
@bot.on_message(
    filters=(basic_filters & filters.mentioned & tag_filter) & ~filters.private, group=2
)
async def mention_logger(bot: BOT, message: Message):
    for entity in message.entities or []:
        if (
            entity.type == MessageEntityType.MENTION
            and entity.user
            and entity.user.id == bot.me.id
        ):
            if message.reply_to_message:
                cache_message(message.reply_to_message)
            cache_message(message)
    message.continue_propagation()


@try_
@bot.on_message(
    filters=(basic_filters & (filters.text | filters.media) & tag_filter)
    & ~filters.private,
    group=2,
)
async def username_logger(bot: BOT, message: Message):
    text = message.text or message.caption or ""
    if bot.me.username and bot.me.username in text:
        if message.reply_to_message:
            cache_message(message.reply_to_message)
        cache_message(message)
    message.continue_propagation()


@try_
def cache_message(message: Message):
    id = message.chat.id
    if id in MESSAGE_CACHE.keys():
        if len(MESSAGE_CACHE[id]) > 10:
            bot.log.error("Flood detected, Message not cached.")
            return
        MESSAGE_CACHE[id].append(message)
    else:
        MESSAGE_CACHE[id] = [message]


@try_
async def runner():
    if not (Config.TAG_LOGGER or Config.PM_LOGGER):
        return
    while True:
        cached_keys = list(MESSAGE_CACHE.keys())
        if not cached_keys:
            await asyncio.sleep(5)
            continue
        first_key = cached_keys[0]
        cached_list = MESSAGE_CACHE.copy()[first_key]
        if not cached_list:
            MESSAGE_CACHE.pop(first_key)
        for idx, msg in enumerate(cached_list):
            if msg.chat.type == ChatType.PRIVATE:
                if idx == 0:
                    global LAST_PM_LOGGED_ID
                    LAST_PM_LOGGED_ID = first_key
                await log_pm(message=msg, key=first_key)
            else:
                await log_chat(message=msg)
            MESSAGE_CACHE[first_key].remove(msg)
            await asyncio.sleep(5)
        await asyncio.sleep(15)


async def log_pm(message: Message, key):
    if LAST_PM_LOGGED_ID != key:
        await bot.send_message(
            chat_id=Config.MESSAGE_LOGGER_CHAT,
            text=f"#PM\n{message.from_user.mention} [{message.from_user.id}]",
        )
    try:
        await message.forward(Config.MESSAGE_LOGGER_CHAT)
    except MessageIdInvalid:
        await log_deleted_message(message)


async def log_chat(message: Message):
    try:
        logged = await message.forward(Config.MESSAGE_LOGGER_CHAT)
        await logged.reply(
            text=f"#TAG\n{message.from_user.mention} [{message.from_user.id}]\nMessage: <a href='{message.link}'>Link</a>",
        )
    except MessageIdInvalid:
        await log_deleted_message(message)


@try_
async def log_deleted_message(message: Message):
    notice = f"{message.from_user.mention} [{message.from_user.id}] deleted this message.\n\n---\n\nMessage: <a href='{message.link}'>Link</a>\n\n---\n\n"
    if not message.media:
        await bot.send_message(
            chat_id=Config.MESSAGE_LOGGER_CHAT,
            text=f"{notice}Text:\n{message.text}",
            disable_web_page_preview=True,
        )
        return
    kwargs = dict(
        chat_id=Config.MESSAGE_LOGGER_CHAT,
        caption=f"{notice}Caption:\n{message.caption or 'No Caption in media.'}",
    )
    if message.photo:
        await bot.send_photo(**kwargs, photo=message.photo.file_id)
    elif message.audio:
        await bot.send_audio(**kwargs, audio=message.audio.file_id)
    elif message.animation:
        await bot.send_animation(
            **kwargs, animation=message.animation.file_id, unsave=True
        )
    elif message.document:
        await bot.send_document(
            **kwargs, document=message.document.file_id, force_document=True
        )
    elif message.video:
        await bot.send_video(**kwargs, video=message.video.file_id)
    elif message.voice:
        await bot.send_voice(**kwargs, voice=message.voice.file_id)
    elif message.sticker:
        await bot.send_sticker(
            chat_id=Config.MESSAGE_LOGGER_CHAT, sticker=message.sticker.file_id
        )
    else:
        await bot.send_message(chat_id=Config.MESSAGE_LOGGER_CHAT, text=str(message))