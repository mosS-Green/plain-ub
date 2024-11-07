from functools import wraps

from pyrogram.raw.types.messages import BotResults
from ub_core import BOT, Message


def run_with_timeout_guard(func):
    @wraps(func)
    async def inner(bot: BOT, message: Message):
        try:
            query_id, result_id, error = await func(bot, message)

            if error:
                await message.reply(error)
                return

            await bot.send_inline_bot_result(
                chat_id=message.chat.id, query_id=query_id, result_id=result_id
            )

        except Exception as e:
            await message.reply(str(e), del_in=10)

    return inner


@BOT.add_cmd("st")
@run_with_timeout_guard
async def last_fm_now(bot: BOT, message: Message):
    """
    CMD: ST
    INFO: Check LastFM Status
    USAGE: .ln
    """

    result: BotResults = await bot.get_inline_bot_results(bot="lastfmrobot")

    if not result.results:
        return None, None, "No results found."

    return result.query_id, result.results[0].id, ""


@BOT.add_cmd("sp")
@run_with_timeout_guard
async def spotipie_now(bot: BOT, message: Message):
    """
    CMD: SP
    INFO: Check Spotipie Now
    USAGE: .sn
    """

    result: BotResults = await bot.get_inline_bot_results(bot="spotipiebot")

    if not result.results:
        return None, None, "No results found."
        
    return result.query_id, result.results[0].id, ""


@BOT.add_cmd("dl")
@run_with_timeout_guard
async def rsdl(bot: BOT, message: Message):
    """
    CMD: DL
    INFO: use bitch's bot
    USAGE: .dl link
    """

    results = await bot.get_inline_bot_results("rsdl_bot", message.input)

    if results.results:
        first_result = results.results[0]
        await message.reply_inline_bot_result(
            query_id=results.query_id,
            result_id=first_result.id
        )
    else:
        await message.reply("No results found.")
