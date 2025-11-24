import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio
)

TOKEN = os.environ.get("TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

active_sessions = {}
cases = {}
reverse_cases = {}
active_case_for_owner = None


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/call")],
            [KeyboardButton(text="/stop")]
        ],
        resize_keyboard=True
    )


def admin_menu():
    kb = []
    for case_id in cases:
        kb.append([KeyboardButton(text=f"case_{case_id}")])

    if not kb:
        kb = [[KeyboardButton(text="Нет активных кейсов")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer(
        "<b>Добро пожаловать!</b>\n"
        "/call — начать диалог\n"
        "/stop — завершить",
        reply_markup=main_menu()
    )


@dp.message(F.text == "/call")
async def call(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if user_id == OWNER_ID:
        await message.answer("Вы владелец", reply_markup=admin_menu())
        return

    if user_id in active_sessions:
        await message.answer("У вас уже есть активный диалог.")
        return

    case_id = len(cases) + 1

    active_sessions[user_id] = True
    cases[case_id] = user_id
    reverse_cases[user_id] = case_id

    user_display = f"@{username}" if username else f"<code>{user_id}</code>"

    await message.answer(
        "Диалог открыт! Пишите сообщения.",
        reply_markup=main_menu()
    )

    await bot.send_message(
        OWNER_ID,
        f"📩 Новый кейс #{case_id}\nПользователь: {user_display}",
        reply_markup=admin_menu()
    )


@dp.message(F.text == "/stop")
async def stop(message: Message):
    user_id = message.from_user.id

    if user_id not in active_sessions:
        await message.answer("У вас нет активного диалога.")
        return

    case_id = reverse_cases[user_id]

    del active_sessions[user_id]
    del reverse_cases[user_id]
    del cases[case_id]

    await message.answer("Диалог завершён.", reply_markup=main_menu())
    await bot.send_message(OWNER_ID, f"❌ Кейс #{case_id} закрыт.", reply_markup=admin_menu())


@dp.message(F.text.regexp(r"case_\d+"))
async def open_case(message: Message):
    global active_case_for_owner
    if message.from_user.id != OWNER_ID:
        return

    case_id = int(message.text.split("_")[1])
    if case_id not in cases:
        await message.answer("Кейс уже закрыт.", reply_markup=admin_menu())
        return

    active_case_for_owner = cases[case_id]
    await message.answer(
        f"Открыт кейс #{case_id}\nПользователь: <code>{active_case_for_owner}</code>",
        reply_markup=admin_menu()
    )


# ---------- OWNER replies ----------
@dp.message(F.from_user.id == OWNER_ID)
async def owner_reply(message: Message):
    global active_case_for_owner

    if not active_case_for_owner:
        await message.answer("Выберите кейс.", reply_markup=admin_menu())
        return

    # TEXT
    if message.text:
        await bot.send_message(active_case_for_owner, f"✉ Сообщение владельца:\n{message.text}")
        return

    # PHOTO
    if message.photo:
        await bot.send_photo(active_case_for_owner, message.photo[-1].file_id, caption=message.caption or "")
        return

    # VIDEO
    if message.video:
        await bot.send_video(active_case_for_owner, message.video.file_id, caption=message.caption or "")
        return

    # DOCUMENT
    if message.document:
        await bot.send_document(active_case_for_owner, message.document.file_id, caption=message.caption or "")
        return

    # AUDIO
    if message.audio:
        await bot.send_audio(active_case_for_owner, message.audio.file_id, caption=message.caption or "")
        return

    # STICKER
    if message.sticker:
        await bot.send_sticker(active_case_for_owner, message.sticker.file_id)
        return


# ---------- USER messages ----------
@dp.message()
async def user_message(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if user_id == OWNER_ID:
        return

    if user_id not in active_sessions:
        return

    case_id = reverse_cases[user_id]
    user_display = f"@{username}" if username else f"<code>{user_id}</code>"

    # TEXT
    if message.text:
        await bot.send_message(
            OWNER_ID,
            f"📨 Кейс #{case_id}\nОт {user_display}:\n{message.text}",
            reply_markup=admin_menu()
        )
        await message.answer("Отправлено.")
        return

    # PHOTO
    if message.photo:
        await bot.send_photo(
            OWNER_ID, message.photo[-1].file_id,
            caption=f"📷 Фото из кейса #{case_id}\nОт {user_display}"
        )
        await message.answer("Фото доставлено.")
        return

    # VIDEO
    if message.video:
        await bot.send_video(
            OWNER_ID, message.video.file_id,
            caption=f"📹 Видео из кейса #{case_id}\nОт {user_display}"
        )
        await message.answer("Видео доставлено.")
        return

    # DOCUMENT
    if message.document:
        await bot.send_document(
            OWNER_ID, message.document.file_id,
            caption=f"📄 Документ из кейса #{case_id}\nОт {user_display}"
        )
        await message.answer("Документ доставлен.")
        return

    # AUDIO
    if message.audio:
        await bot.send_audio(
            OWNER_ID, message.audio.file_id,
            caption=f"🎵 Аудио из кейса #{case_id}\nОт {user_display}"
        )
        await message.answer("Аудио доставлено.")
        return

    # STICKER
    if message.sticker:
        await bot.send_sticker(OWNER_ID, message.sticker.file_id)
        await message.answer("Стикер доставлен.")
        return


async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
