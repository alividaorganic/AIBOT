import asyncio
import logging
import os
import random
import urllib.parse

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile, FSInputFile

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"


@dp.message(CommandStart())
async def start_handler(message: Message):
    welcome_text = (
        "🎨 <b>RasmAI</b>ga xush kelibsiz!\n\n"
        "✨ Menga xohlagan tasvirni so'z bilan yozing — men uni jonlantiraman.\n\n"
        "💡 <b>Masalan:</b>\n"
        "🌅 <i>\"Tog'lar orasida quyosh botishi, real fotosurat uslubida\"</i>\n"
        "🐉 <i>\"Bulutlar ustida uchayotgan ajdaho, fantastik uslub\"</i>\n"
        "🏙 <i>\"Kechki Toshkent shahri, neon chiroqlar bilan\"</i>\n\n"
        "👇 Hoziroq birinchi rasmingizni so'rang!"
    )
    try:
        photo = FSInputFile("bot_logo.png")
        await message.answer_photo(photo, caption=welcome_text, parse_mode="HTML")
    except FileNotFoundError:
        await message.answer(welcome_text, parse_mode="HTML")


@dp.message(F.text)
async def generate_image_handler(message: Message):
    prompt = message.text.strip()
    if not prompt:
        return

    status_msg = await message.answer("Rasm yaratilmoqda, biroz kuting...")

    try:
        encoded_prompt = urllib.parse.quote(prompt)
        seed = random.randint(1, 999999)
        url = (
            f"{POLLINATIONS_URL.format(prompt=encoded_prompt)}"
            f"?width=1024&height=1024&seed={seed}&nologo=true"
            f"&model=flux&nofeed=true"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"Cache-Control": "no-cache"},
                timeout=aiohttp.ClientTimeout(total=90),
            ) as resp:
                if resp.status != 200:
                    await status_msg.edit_text(
                        f"Xatolik yuz berdi (status {resp.status}). Qaytadan urinib ko'ring."
                    )
                    return
                image_bytes = await resp.read()

        photo = BufferedInputFile(image_bytes, filename="generated.png")
        await message.answer_photo(photo, caption=f'"{prompt}"')
        await status_msg.delete()

    except Exception as e:
        logging.exception("Image generation failed")
        await status_msg.edit_text(f"Xatolik yuz berdi: {e}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
