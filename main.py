import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ContentType
from flask import Flask
from threading import Thread

# ------------------------
# Конфигурация
# ------------------------
TOKEN = "8555813391:AAEeQmqWmVd79iOjId2-4QmXJ38_I-cfnuA"
OWNER_ID = 6923254118

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ------------------------
# Хранилища
# ------------------------
active_sessions = {}      # user_id -> True
cases = {}                # case_id -> user_id
reverse_cases = {}        # user_id -> case_id
active_case_for_owner = None  # текущий выбранный кейс владельцем
usernames = {}            # user_id -> username

# ------------------------
# Главное меню
# ------------------------
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/call")],
            [KeyboardButton(text="/stop")]
        ],
        resize_keyboard=True
    )

# ------------------------
# Меню владельца с кейсами
# ------------------------
def admin_menu():
    kb = []
    for case_id, user_id in cases.items():
        username = usernames.get(user_id)
        display = f"@{username}" if username else f"<code>{user_id}</code>"
        kb.append([KeyboardButton(text=f"case_{case_id} ({display})")])
    if not kb:
        kb = [[KeyboardButton(text="Нет активных кейсов")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ------------------------
# /start
# ------------------------
@dp.message(F.text == "/start")
async def start(message: Message):
    usernames[message.from_user.id] = message.from_user.username
    await message.answer(
        "<b>Добро пожаловать!</b>\n\n"
        "Команды:\n"
        "/call — открыть диалог с владельцем\n"
        "/stop — завершить диалог\n\n"
        "Выберите действие:",
        reply_markup=main_menu()
    )

# ------------------------
# /call — открытие диалога
# ------------------------
@dp.message(F.text == "/call")
async def call(message: Message):
    user_id = message.from_user.id
    usernames[user_id] = message.from_user.username

    if user_id == OWNER_ID:
        await message.answer("<b>Вы владелец</b>", reply_markup=admin_menu())
        return

    if user_id in active_sessions:
        await message.answer("У вас уже есть активный диалог.")
        return

    case_id = len(cases) + 1
    cases[case_id] = user_id
    reverse_cases[user_id] = case_id
    active_sessions[user_id] = True

    user_display = f"@{usernames[user_id]}" if usernames[user_id] else f"<code>{user_id}</code>"

    await message.answer(
        "<b>Диалог открыт!</b>\n"
        "Теперь вы можете общаться с владельцем.\n"
        "Чтобы выйти, нажмите /stop."
    )

    await bot.send_message(
        OWNER_ID,
        f"📩 Новый кейс #{case_id}\nПользователь: {user_display}",
        reply_markup=admin_menu()
    )

# ------------------------
# /stop — завершение диалога
# ------------------------
@dp.message(F.text == "/stop")
async def stop(message: Message):
    user_id = message.from_user.id

    if user_id not in active_sessions:
        await message.answer("У вас нет активной сессии.")
        return

    case_id = reverse_cases[user_id]

    del active_sessions[user_id]
    del reverse_cases[user_id]
    del cases[case_id]

    await message.answer("Диалог завершён.", reply_markup=main_menu())
    await bot.send_message(OWNER_ID, f"❌ Кейс #{case_id} закрыт.", reply_markup=admin_menu())

# ------------------------
# Владелец выбирает кейс
# ------------------------
@dp.message(F.text.regexp(r"case_\d+"))
async def open_case(message: Message):
    global active_case_for_owner
    if message.from_user.id != OWNER_ID:
        return

    case_id = int(message.text.split("_")[1])
    if case_id not in cases:
        await message.answer("Кейс не найден.", reply_markup=admin_menu())
        return

    active_case_for_owner = cases[case_id]
    display_name = usernames.get(active_case_for_owner) or str(active_case_for_owner)
    await message.answer(
        f"Вы выбрали кейс #{case_id}.\nПользователь: @{display_name}\n"
        "Теперь пишите сообщение:",
        reply_markup=admin_menu()
    )

# ------------------------
# Владелец пишет пользователю
# ------------------------
@dp.message(F.from_user.id == OWNER_ID)
async def owner_reply(message: Message):
    global active_case_for_owner
    if not active_case_for_owner:
        await message.answer("Выберите кейс.", reply_markup=admin_menu())
        return

    if message.content_type == ContentType.TEXT:
        await bot.send_message(active_case_for_owner, f"✉ Ответ владельца:\n{message.text}")
    else:
        await message.copy_to(active_case_for_owner)

# ------------------------
# Пользователь пишет владельцу
# ------------------------
@dp.message()
async def user_message(message: Message):
    user_id = message.from_user.id
    usernames[user_id] = message.from_user.username

    if user_id == OWNER_ID or user_id not in active_sessions:
        return

    case_id = reverse_cases[user_id]
    user_display = f"@{usernames[user_id]}" if usernames[user_id] else f"<code>{user_id}</code>"

    if message.content_type == ContentType.TEXT:
        await bot.send_message(
            OWNER_ID,
            f"📨 Сообщение из кейса #{case_id}\nОт {user_display}:\n{message.text}",
            reply_markup=admin_menu()
        )
    else:
        await message.copy_to(OWNER_ID)

    await message.answer("Сообщение доставлено. Ожидайте ответа.")

# ------------------------
# Запуск бота
# ------------------------
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

# ------------------------
# Keep-alive для Replit
# ------------------------
app = Flask("")

@app.route("/")
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

t = Thread(target=run)
t.start()

if __name__ == "__main__":
    asyncio.run(main())
