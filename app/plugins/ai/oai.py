import os
from openai import OpenAI
from app import BOT, Message, bot
import requests
from io import BytesIO

apikey = os.environ.get("FAPIKEY")

client = OpenAI(api_key = apikey, base_url = "https://fresedgpt.space/v1")

@bot.add_cmd(cmd="g")
async def gpt(bot: BOT, message: Message):
    prompt = message.input

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = f"4o: {response.choices[0].message.content}"
    await message.reply(response_text)


@bot.add_cmd(cmd="img")
async def generate_image(bot: BOT, message: Message):
    prompt = message.input

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024"
    )

    image_url = response.data[0].url
    image_data = requests.get(image_url).content
    image_file = BytesIO(image_data)
    image_file.name = "generated_image.jpg"

    await bot.send_photo(chat_id=message.chat.id, photo=image_file)
