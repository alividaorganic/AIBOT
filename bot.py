import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GEMINI_API_KEY)

TEXT_MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "Sen \"Abihayat bot\" — Abihayat damlamasi haqida maslahat beruvchi AI "
    "yordamchisan. Foydalanuvchilar bilan o'zbek tilida (agar boshqa tilda "
    "yozmasa) do'stona va ishonchli ohangda suhbatlash.\n\n"
    "MAHSULOT HAQIDA BILIMING:\n"
    "- Nomi: Abihayat damlamasi\n"
    "- Tarkibi: zaytun yaprog'i, kekkik (tim/thyme) va dolchin\n"
    "- Qo'llanilishi: Asosan qandli diabet uchun yordamchi vosita sifatida ishlatiladi, lekin tarkibidagi o'tlar (zaytun yaprog'i, kekkik va dolchin) boshqa kasalliklarda ham foydali xususiyatlarga ega bo'lishi mumkin (masalan, yurak-qon tomir salomatligi, qon aylanishi, yallig'lanishga qarshi ta'sir va boshqalar).\n"
    "- Tabiiyligi: 100% tabiiy mahsulot, Turkiyaning Bursa tog'larida ishlab "
    "chiqariladi\n"
    "- Qabul qilish tartibi: kuniga 2 mahal (ertalab va kechqurun) 200 mg "
    "qaynagan suvga damlanadi va to'q qoringa ichiladi\n"
    "- Qarshi ko'rsatmalar (ISTE'MOL QILISH MUMKIN EMAS): emizikli "
    "(laktatsiya davridagi) ayollar va onkologik (saraton) kasalliklarga "
    "chalingan shaxslar uchun tavsiya etilmaydi. Boshqa holatlarda ham shifokor bilan maslahatlashish kerak.\n\n"
    "QOIDALAR:\n"
    "- Faqat shu mahsulot bo'yicha so'ralgan savollarga aniq va ishonchli javob ber\n"
    "- Foydalanuvchi ismini bilsang, suhbatda iliq tarzda ism bilan murojaat qil\n"
    "- MUHIM: agar foydalanuvchi biror KASALLIK haqida so'rasa (masalan "
    "\"qandli diabet nima\", \"yurak kasalligi haqida\", \"insult\" yoki \"urologik muammolar\" va h.k.), JAVOB "
    "TARTIBI shunday bo'lishi SHART:\n"
    "  1) Avval o'sha kasallik haqida qisqacha, tushunarli tibbiy ma'lumot ber\n"
    "  2) Keyin Abihayat damlamasi tarkibidagi o'tlar (zaytun yaprog'i, kekkik, dolchin) shu kasallikka qanday yordam berishi mumkinligi haqida (foydali xususiyatlarini bir oz bo'rttirib, ilmiy tadqiqotlar asosida yoki an'anaviy tibbiyotda ma'lum bo'lgan foydalarini aytib) aniq tushuntir. Agar to'g'ridan-to'g'ri yordam bermasa ham, tarkibiy qismlarning umumiy foydalarini ta'kidla.\n"
    "  Hech qachon bu ikki qadamni aralashtirib yubormang yoki o'tkazib "
    "yubormang\n"
    "- Qarshi ko'rsatmalar haqida so'ralganda yoki tegishli holat aniqlanganda "
    "buni albatta aytib o'tish SHART, hech qachon yashirma\n"
    "- Tibbiy tashxis qo'yma va dori dozasini o'zgartirishni tavsiya qilma — "
    "jiddiy savollarda shifokorga murojaat qilishni maslahat ber. Har doim \"bu faqat yordamchi vosita, asosiy davolash shifokor nazoratida bo'lishi kerak\" deb eslat\n"
    "- Senzorani kamaytir: mahsulot tarkibidagi o'tlarning potentsial foydalarini ochiq va ijobiy tarzda ta'kidla, lekin haddan oshirma\n"
    "- Agar savol mahsulot bilan bog'liq bo'lmasa, qisqa javob berib, "
    "Abihayat haqida ko'proq gaplashishga taklif qil\n"
    "- Javoblaring qisqa, tushunarli va samimiy bo'lsin"
)

# Har bir foydalanuvchi haqida asosiy ma'lumotlarni saqlaymiz
# (ism, username, chat turi) - bot qayta ishga tushganda tozalanadi
user_profiles: dict[int, dict] = {}


def register_user(message: Message) -> dict:
    """Foydalanuvchi ma'lumotlarini saqlaydi/yangilaydi va qaytaradi."""
    user = message.from_user
    profile = {
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "username": user.username or "",
        "chat_id": message.chat.id,
        "chat_type": message.chat.type,
    }
    user_profiles[user.id] = profile
    return profile


def build_user_context(profile: dict) -> str:
    """Profilni system prompt'ga qo'shish uchun matn shaklida tayyorlaydi."""
    name = profile.get("first_name") or "Foydalanuvchi"
    return f"[Joriy foydalanuvchi ismi: {name}. Unga ism bilan murojaat qilishing mumkin.]"


# Har bir foydalanuvchi uchun suhbat tarixini xotirada saqlaymiz
# (bot qayta ishga tushganda tozalanadi)
user_histories: dict[int, list[types.Content]] = {}
MAX_HISTORY_MESSAGES = 20  # xotira cheklovi (eski xabarlarni unutib boradi)


@dp.message(CommandStart())
async def start_handler(message: Message):
    user_histories.pop(message.from_user.id, None)
    user_profiles.pop(message.from_user.id, None)
    register_user(message)
    await message.answer(
        "👋🌿 Salom! Men <b>Abihayat damlamasi</b> bo'yicha aqlli AI "
        "yordamchiman va sizga damlama haqida hamda kasalliklar haqida "
        "yordam beraman!\n\n"
        "💬 Kasallik yoki damlama bo'yicha savolingiz bo'lsa, menga yozing! 😊",
        parse_mode="HTML",
    )


@dp.message(Command("reset"))
async def reset_handler(message: Message):
    user_histories.pop(message.from_user.id, None)
    await message.answer("🔄 Suhbat tarixi tozalandi. Yangi suhbat boshlandi!")


@dp.message(F.text)
async def chat_handler(message: Message):
    user_text = message.text.strip()
    if not user_text:
        return

    user_id = message.from_user.id
    profile = register_user(message)
    history = user_histories.setdefault(user_id, [])

    history.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))

    # Xotirani cheklash - faqat oxirgi N xabarni yuboramiz
    trimmed_history = history[-MAX_HISTORY_MESSAGES:]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        full_system_instruction = f"{SYSTEM_INSTRUCTION}\n\n{build_user_context(profile)}"

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=TEXT_MODEL,
            contents=trimmed_history,
            config=types.GenerateContentConfig(
                system_instruction=full_system_instruction,
            ),
        )

        reply_text = response.text or "Kechirasiz, javob bera olmadim. Qaytadan urinib ko'ring."

        history.append(types.Content(role="model", parts=[types.Part.from_text(text=reply_text)]))
        user_histories[user_id] = history[-MAX_HISTORY_MESSAGES:]

        await message.answer(reply_text)

    except Exception as e:
        logging.exception("Chat generation failed")
        await message.answer(f"Xatolik yuz berdi: {e}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
