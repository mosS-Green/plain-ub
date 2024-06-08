from app import bot, Message
from pyrogram.enums import ParseMode
from g4f.client import Client
from g4f.client.async_client import AsyncClient
from g4f.Provider import DeepInfraImage, Liaobots


@bot.add_cmd(cmd="llm")
async def llama(bot, message: Message):
    client = AsyncClient(
    provider = DeepInfraImage
)

    response = await client.images.generate(
        model = "stability-ai/sdxl",
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

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message.input }],
    )

    await message.reply(
                text = f"4o: {response.choices[0].message.content}"
            )
