import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from tronapi import Tron
import config

# Ініціалізація бота і диспетчера
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Ініціалізація Tron API
tron = Tron(full_node=config.TRON_FULL_NODE)
tron.private_key = config.TRON_PRIVATE_KEY

# Словник для зберігання стану користувача
user_data = {}

# Стартова команда /start але її треба  забирати та привязувати до фронту
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("USDT", callback_data='select_currency'))
    keyboard.add(InlineKeyboardButton("Назад", callback_data='go_back'))
    
    await message.answer("Виберіть криптовалюту:", reply_markup=keyboard)

# Обробка вибору криптовалюти
@dp.callback_query_handler(lambda c: c.data == 'select_currency')
async def process_select_currency(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Tether 20 (TRC-20)", callback_data='select_network'))
    keyboard.add(InlineKeyboardButton("Назад", callback_data='go_back'))

    await bot.answer_callback_query(callback_query.id)
    await bot.edit_message_text(chat_id=callback_query.from_user.id,
                                message_id=callback_query.message.message_id,
                                text="Виберіть мережу:",
                                reply_markup=keyboard)

# Обробка вибору мережі
@dp.callback_query_handler(lambda c: c.data == 'select_network')
async def process_select_network(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.edit_message_text(chat_id=callback_query.from_user.id,
                                message_id=callback_query.message.message_id,
                                text="Введіть адресу свого гаманця:")

    user_data[callback_query.from_user.id] = {}
    user_data[callback_query.from_user.id]['step'] = 'enter_wallet'

# Обробка введення адреси гаманця
@dp.message_handler(lambda message: user_data.get(message.from_user.id, {}).get('step') == 'enter_wallet')
async def handle_wallet_address(message: types.Message):
    wallet_address = message.text
    user_data[message.from_user.id]['wallet_address'] = wallet_address
    user_data[message.from_user.id]['step'] = 'enter_amount'

    await message.answer("Введіть суму в USDT:")

# Обробка введення суми
@dp.message_handler(lambda message: user_data.get(message.from_user.id, {}).get('step') == 'enter_amount')
async def handle_amount(message: types.Message):
    amount = message.text
    user_data[message.from_user.id]['amount'] = amount

    # Розрахунок GAME USD
    game_usd = int(amount) * 5

    # Виводимо кількість GAME USD
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Обміняти", callback_data='confirm_exchange'))
    keyboard.add(InlineKeyboardButton("Назад", callback_data='go_back'))

    await message.answer(f"Ви отримуєте {game_usd} GAME USD", reply_markup=keyboard)

# Підтвердження обміну
@dp.callback_query_handler(lambda c: c.data == 'confirm_exchange')
async def process_confirm_exchange(callback_query: types.CallbackQuery):
    wallet_address = user_data[callback_query.from_user.id]['wallet_address']
    amount = user_data[callback_query.from_user.id]['amount']

    await bot.answer_callback_query(callback_query.id)
    await bot.edit_message_text(chat_id=callback_query.from_user.id,
                                message_id=callback_query.message.message_id,
                                text=f"Чекаємо на підтвердження транзакції на адресу: {wallet_address}. Будь ласка, зачекайте.")
    
    # Запускаємо процес перевірки транзакції
    await monitor_transaction(callback_query.from_user.id, wallet_address, amount)

async def monitor_transaction(user_id, wallet_address, amount):
    # Тут ми будемо періодично перевіряти блокчейн на наявність транзакції
    confirmed = False
    while not confirmed:
        # Використовуємо API для отримання інформації про транзакції
        try:
            # Приклад tron API для отримання транзакцій (можливо знадобиться налаштувати =D)
            transactions = tron.trx.get_transaction(wallet_address)
            
            # Перевіряємо, чи є серед транзакцій потрібна сума
            for transaction in transactions:
                if transaction['amount'] == int(amount) and transaction['confirmed']:
                    confirmed = True
                    break
            
            if confirmed:
                game_usd = int(amount) * 5
                await bot.send_message(user_id, f"Транзакцію підтверджено! Ви отримали {game_usd} GAME USD.")
            else:
                await asyncio.sleep(10)  # Очікуємо 10 секунд перед наступною перевіркою

        except Exception as e:
            print(f"Помилка при перевірці транзакцій: {e}")
            await asyncio.sleep(10)  # Чекаємо 10 секунд перед наступною спробою

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)