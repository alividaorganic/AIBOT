import asyncio
import base64
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile
from google import genai

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GEMINI_API_KEY)

IMAGE_MODEL = "gemini-2.5-flash-image"


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Salom! Menga rasm tasvirini matn qilib yozing, men sizga rasm "
        "generatsiya qilib beraman.\n\n"
        "Masalan: \"Tog'lar orasida quyosh botishi, real fotosurat uslubida\""
    )


@dp.message(F.text)
async def generate_image_handler(message: Message):
    prompt = message.text.strip()
    if not prompt:
        return

    status_msg = await message.answer("Rasm yaratilmoqda, biroz kuting...")

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=IMAGE_MODEL,
            contents=prompt,
        )

        image_bytes = None
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None) is not None:
                image_bytes = part.inline_data.data
                break

        if image_bytes is None:
            await status_msg.edit_text(
                "Kechirasiz, rasm yaratib bo'lmadi. Boshqacha so'rov bilan urinib ko'ring."
            )
            return

        # inline_data.data sometimes comes already as raw bytes, sometimes base64 str
        if isinstance(image_bytes, str):
            image_bytes = base64.b64decode(image_bytes)

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
