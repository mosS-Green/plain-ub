from app import bot, Message
from pyrogram.enums import ParseMode
from g4f.client import Client
from g4f.Provider import Airforce, Liaobots


@bot.add_cmd(cmd="if")
async def af(bot, message: Message):
    client = AsyncClient(
    provider = Airforce
)

    response = await client.images.async_generate(
        model = "flux",
        prompt = f"{message.input}, masterpiece, leica photgraph, texture, perfect lighting, dslr"
    )
    image_url = response.data[0].url
    await message.reply_photo(
        photo=image_url
    )

@bot.add_cmd(cmd="g")
async def gpt(bot, message: Message):
    client = AsyncClient(
        provider = Liaobots
    )

    response = await client.chat.completions.async_create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message.input }],
    )

    await message.reply(
                text = f"4o: {response.choices[0].message.content}"
            )

@bot.add_cmd(cmd="gm")
async def gpt(bot, message: Message):
    client = AsyncClient(
        provider = Liaobots
    )

    response = await client.chat.completions.async_create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message.input }],
    )

    await message.reply(
                text = f"4o-mini: {response.choices[0].message.content}"
            )
