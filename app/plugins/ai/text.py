import json
import mimetypes
import os
import pickle
from io import BytesIO

from pyrogram import filters
from pyrogram.enums import ParseMode

from app import BOT, Convo, Message, bot, Config
from google.ai import generativelanguage as glm
import google.generativeai as genai
from app.plugins.ai.models import TEXT_MODEL, MEDIA_MODEL, IMAGE_MODEL, basic_check, get_response_text, SAFETY_SETTINGS, GENERATION_CONFIG
from app.plugins.ai.media import handle_photo, handle_audio

CONVO_CACHE: dict[str, Convo] = {}

SPECIFIC_GROUP_ID = [-1001898736703, -1002010754513]
SPG_ID = -1001939171299
CONV = []

@bot.add_cmd(cmd="fh")
async def fetch_history(bot=bot, message=None):
    history_message_id = int(os.environ.get("HISTORY_MESSAGE_ID"))
    past_message_id = int(os.environ.get("PAST_MESSAGE_ID"))
    assist_message_id = int(os.environ.get("ASSIST_MESSAGE_ID"))
    
    history_message, past_message, assist_message = await bot.get_messages(
        chat_id=Config.LOG_CHAT, message_ids=[history_message_id, past_message_id, assist_message_id]
    )
    
    history = json.loads(history_message.text)
    
    global MHIST
    MHIST = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",
        generation_config=GENERATION_CONFIG,
        system_instruction=history,
        safety_settings=SAFETY_SETTINGS,
    )
    
    past = json.loads(past_message.text)
    
    global MPAST
    MPAST = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",
        generation_config=GENERATION_CONFIG,
        system_instruction=past,
        safety_settings=SAFETY_SETTINGS,
    )
    
    assist = json.loads(assist_message.text)
    
    global MASSIST
    MASSIST = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",
        generation_config=GENERATION_CONFIG,
        system_instruction=assist,
        safety_settings=SAFETY_SETTINGS,
    )
    
    if message is not None:
        await message.reply("Done.")

@bot.add_cmd(cmd = "ah")
async def fix(bot: BOT, message: Message):
    global CONV
    if message.replied:
        CONV = json.loads(message.replied.text)
    else:
        CONV = []

@bot.add_cmd(cmd=["aic", "rxc"])
async def ai_chat(bot: BOT, message: Message):
    """
    CMD: AIC
    INFO: Have a Conversation with Gemini AI.
    USAGE:
        .aichat hello
        keep replying to AI responses
        After 5 mins of Idle bot will export history and stop chat.
        use .load_history to continue
    """
    if not await basic_check(message):
        return
    if message.chat.id in SPECIFIC_GROUP_ID:
        onefive = MPAST
    elif message.chat.id == SPG_ID:
        onefive = MASSIST
    else:
        onefive = MHIST
    MODEL = onefive if message.cmd == "rxc" else MEDIA_MODEL
    chat = MODEL.start_chat(history=[])
    await do_convo(chat=chat, message=message)


@bot.add_cmd(cmd=["load_history", "lxc"])
async def history_chat(bot: BOT, message: Message):
    """
    CMD: LOAD_HISTORY
    INFO: Load a Conversation with Gemini AI from previous session.
    USAGE:
        .load_history {question} [reply to history document]
    """
    if not await basic_check(message):
        return
    if message.chat.id in SPECIFIC_GROUP_ID:
        onefive = MPAST
    elif message.chat.id == SPG_ID:
        onefive = MASSIST
    else:
        onefive = MHIST
    reply = message.replied
    
    if (
        not reply
        or not reply.document
        or not reply.document.file_name
        or reply.document.file_name != "AI_Chat_History.pkl"
    ):
        await message.reply("Reply to a Valid History file.")
        return
        
    resp = await message.reply("<i>Loading History...</i>")
    doc: BytesIO = (await reply.download(in_memory=True)).getbuffer()  # NOQA
    history = pickle.loads(doc)
    await resp.edit("<i>History Loaded... Resuming chat</i>")
    MODEL= onefive if message.cmd == "lxc" else TEXT_MODEL
    chat = MODEL.start_chat(history=history)
    await do_convo(chat=chat, message=message)


async def do_convo(chat, message: Message):
    prompt = message.input
    reply_to_message_id = message.id

    old_convo = CONVO_CACHE.get(message.unique_chat_user_id)

    if old_convo:
        Convo.CONVO_DICT[message.chat.id].remove(old_convo)

    convo_obj = Convo(
        client=message._client,
        chat_id=message.chat.id,
        filters=generate_filter(message),
        timeout=180,
        check_for_duplicates=False,
    )

    CONVO_CACHE[message.unique_chat_user_id] = convo_obj

    try:
        async with convo_obj:
            while True:
                ai_response = await chat.send_message_async(prompt)
                ai_response_text = get_response_text(ai_response)
                text = ai_response_text
                _, prompt_message = await convo_obj.send_message(
                    text=text,
                    reply_to_message_id=reply_to_message_id,
                    parse_mode=ParseMode.MARKDOWN,
                    get_response=True,
                )
                prompt, reply_to_message_id = prompt_message.text, prompt_message.id
    except TimeoutError:
        await export_history(chat, message)

    CONVO_CACHE.pop(message.unique_chat_user_id, 0)


def generate_filter(message: Message):
    async def _filter(_, __, msg: Message):
        if (
            not msg.text
            or not msg.from_user
            or msg.from_user.id != message.from_user.id
            or not msg.reply_to_message
            or not msg.reply_to_message.from_user
            or msg.reply_to_message.from_user.id != message._client.me.id
        ):
            return False
        return True

    return filters.create(_filter)


async def export_history(chat, message: Message):
    doc = BytesIO(pickle.dumps(chat.history))
    doc.name = "AI_Chat_History.pkl"
    caption = get_response_text(
        await chat.send_message_async("Give our conversation a concise title.")
    )
    await bot.send_document(chat_id=message.from_user.id, document=doc, caption=caption)

@bot.add_cmd(cmd=["ai","ry"])
async def question(bot: BOT, message: Message):
    """
    CMD: AI
    INFO: Ask a question to Gemini AI.
    USAGE: .ai what is the meaning of life.
    """

    prompt = message.input
    MODEL = MEDIA_MODEL if message.cmd == "ai" else MHIST
    
    response = await MODEL.generate_content_async(prompt)

    response_text = get_response_text(response)

    if message.cmd == "ai":
        await message.edit(
            text=f"```\n{prompt}```**AI**:\n{response_text.strip()}",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await message.edit(
            text=f"```\n{prompt}```**Reya**:\n{response_text.strip()}",
            parse_mode=ParseMode.MARKDOWN,
        )

@bot.add_cmd(cmd=["r","rx"])
async def reya(bot: BOT, message: Message):
    """
    CMD: R
    INFO: Ask a question to Reya.
    USAGE: .r How to be strong?
    """
    if not (await basic_check(message)):  # fmt:skip
        return
    if message.chat.id in SPECIFIC_GROUP_ID:
        onefive = MPAST
    elif message.chat.id == SPG_ID:
        onefive = MASSIST
    else:
        onefive = MHIST
    MODEL = MEDIA_MODEL if message.cmd == "r" else onefive
    replied = message.replied

    if replied and message.input:
        prompt = f"{replied.text}\n\n{message.input}"
    elif not message.input:
        prompt = replied.text
    else:
        prompt = message.input

    if replied and replied.photo:
        imgprmpt = message.input
        reply = message.replied
        message_response = await message.reply("...")

        response_text = await handle_photo(imgprmpt, reply, MODEL)

        await message_response.edit(response_text)
    
    elif replied and (replied.audio or replied.voice):
        audprmpt = message.input
        reply = message.replied
        message_response = await message.reply("...")
        
        response_text = await handle_audio(audprmpt, reply, MODEL)
      
        await message_response.edit(response_text)

    else:
        convo = MODEL.start_chat(history = CONV)
        response = convo.send_message(prompt)
        response_text = get_response_text(response)
        message_response = await message.reply("...")
        await message_response.edit(response_text)

@bot.add_cmd(cmd = "f")
async def fix(bot: BOT, message: Message):
    if not (await basic_check(message)):  # fmt:skip
        return
        
    MODEL = MEDIA_MODEL
    prompt = f"REWRITE FOLLOWING MESSAGE AS IS, WITH NO CHANGES TO FORMAT AND SYMBOLS ETC. AND ONLY WITH CORRECTION TO SPELLING ERRORS :- {message.replied.text}"
    
    response = await MODEL.generate_content_async(prompt)
    response_text = get_response_text(response)
    message_response = message.replied
    await message_response.edit(response_text)
