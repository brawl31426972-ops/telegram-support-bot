import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import asyncio

from keep_alive import keep_alive

# Owner TG ID
OWNER_ID = 6923254118

# Token from environment (Scalingo)
TOKEN = os.environ["TOKEN"]

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Active user sessions
active_sessions = {}  # user_id → "active"
cases = {}            # case_id → user_id
case_counter = 0


# ---------------------- MENU KEYBOARD ----------------------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Call", callback_data="call")]
    ])


# ---------------------- /start ----------------------
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "👋 <b>Welcome!</b>\n\n"
        "Это бот для связи.\n"
        "Нажмите кнопку ниже, чтобы начать диалог.",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# ---------------------- USER PRESSES CALL ----------------------
@dp.callback_query(lambda c: c.data == "call")
async def user_call(callback):
    global case_counter

    user_id = callback.from_user.id
    username = callback.from_user.username

    if user_id in active_sessions:
        await callback.answer("Вы уже в диалоге!", show_alert=True)
        return

    case_counter += 1
    case_id = case_counter

    active_sessions[user_id] = case_id
    cases[case_id] = user_id

    # Inform user
    await bot.send_message(
        user_id,
        f"📞 Диалог <b>открыт</b>!\n"
        f"Теперь вы можете писать сообщение.\n"
        f"Отправьте /stop чтобы завершить.",
        parse_mode="HTML"
    )

    # Inform owner
    await bot.send_message(
        OWNER_ID,
        f"🆕 <b>Новый кейс #{case_id}</b>\n"
        f"ID: <code>{user_id}</code>\n"
        f"Username: @{username if username else 'нет'}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"Открыть кейс #{case_id}", callback_data=f"case_{case_id}")]
            ]
        )
    )

    await callback.answer()


# ---------------------- OWNER PRESSES CASE BUTTON ----------------------
@dp.callback_query(lambda c: c.data.startswith("case_"))
async def owner_open_case(callback):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    case_id = int(callback.data.split("_")[1])
    user_id = cases.get(case_id)

    if not user_id:
        await callback.answer("Кейс уже закрыт", show_alert=True)
        return

    await callback.message.answer(
        f"🗂 <b>Вы отвечаете пользователю:</b> <code>{user_id}</code>\n"
        f"Напишите сообщение — оно уйдет пользователю.",
        parse_mode="HTML"
    )

    await callback.answer()


# ---------------------- USER SENDS MESSAGE TO OWNER ----------------------
@dp.message()
async def message_router(message: Message):
    user_id = message.from_user.id

    # --- If user is talking to owner ---
    if user_id in active_sessions and user_id != OWNER_ID:
        case_id = active_sessions[user_id]

        # Forward text / media to owner
        if message.text:
            await bot.send_message(
                OWNER_ID,
                f"📩 <b>Сообщение из кейса #{case_id}</b>\n"
                f"<code>{user_id}</code>:\n{message.text}",
                parse_mode="HTML"
            )
        else:
            await message.forward(OWNER_ID)

        # Auto-reply to user
        await message.answer("Сообщение отправлено! Ожидайте ответа.")
        return

    # --- If owner is replying to a case ---
    if user_id == OWNER_ID and message.reply_to_message:
        original_text = message.reply_to_message.text
        if "кейс #" in original_text:
            # Extract the case ID
            case_id = int(original_text.split("кейс #")[1].split("<")[0])
            target = cases.get(case_id)

            if target:
                if message.text:
                    await bot.send_message(target, f"💬 Ответ владельца:\n{message.text}")
                else:
                    await message.copy_to(target)
        return


# ---------------------- /stop ----------------------
@dp.message(Command("stop"))
async def stop_dialog(message: Message):
    user_id = message.from_user.id

    if user_id not in active_sessions:
        await message.answer("Вы не в диалоге.")
        return

    case_id = active_sessions[user_id]

    # Remove case
    del active_sessions[user_id]
    del cases[case_id]

    await message.answer("Диалог завершен. Вы вернулись в меню.", reply_markup=main_menu())

    await bot.send_message(OWNER_ID, f"❌ Кейс #{case_id} закрыт пользователем.")


# ---------------------- RUN ----------------------
async def main():
    keep_alive()  # Start flask server
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
