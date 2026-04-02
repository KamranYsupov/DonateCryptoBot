import asyncio
import sys
import time
import pytonconnect.exceptions

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pytonconnect import TonConnect
from loguru import logger

from app.core.config import settings
from app.handlers.connector import get_connector
from app.handlers.messages import get_comment_message
from app.handlers.utils import disconnect_wallet, connect_wallet
from app.models.telegram_user import DonateStatus
from app.keyboards.donate import get_donate_keyboard
from app.handlers.utils import get_ton_exchange_rate, rub_to_ton
from app.repositories.transaction import RepositoryTransaction

# top_up_router = Router()
#
#
# class MoneyState(StatesGroup):
#     amount = State()


# @top_up_router.message(Command("deposit"))
# async def init(message: Message):
#     # FIXME init handler need to be deleted later, now it's just a plug
#     from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
#
#     keyboard = InlineKeyboardBuilder()
#     keyboard.add(InlineKeyboardButton(text="click", callback_data="donate_1000"))
#
#     donate_keyboard = get_donate_keyboard(
#         buttons={
#             "5.5514 rub": "donate_5.5514",
#             DonateStatus.BASE.value: "donate_1000",
#             DonateStatus.BRONZE.value: "donate_4000",
#             DonateStatus.SILVER.value: "donate_10000",
#             DonateStatus.GOLD.value: "donate_40000",
#             DonateStatus.PLATINUM.value: "donate_100000",
#             DonateStatus.BRILLIANT.value: "donate_400000",
#             "МОЯ КОМАНДА": "team",
#         }
#     )
#
#     await message.answer(
#         text="нажми на кнопку",
#         reply_markup=donate_keyboard,
#     )


# @top_up_router.callback_query(F.data.startswith("donate_"))
# async def command_start_handler(callback: CallbackQuery):
#     # Here we should get donate sum and put it to db
#     donate_amount = float(callback.data.split("_")[-1])
#
#     chat_id = callback.message.chat.id
#     connector = get_connector(chat_id)
#     connected = await connector.restore_connection()
#
#     mk_b = InlineKeyboardBuilder()
#     if connected:
#         mk_b.button(text="Отправить транзакцию", callback_data="send_tr")
#         mk_b.button(text="Отключить", callback_data="disconnect")
#         await callback.message.answer(
#             text="Ваш wallet подключен", reply_markup=mk_b.as_markup()
#         )
#
#     else:
#         wallets_list = TonConnect.get_wallets()
#         for wallet in wallets_list:
#             mk_b.button(text=wallet["name"], callback_data=f'connect:{wallet["name"]}')
#         mk_b.adjust(
#             1,
#         )
#         await callback.message.answer(
#             text="Выберите wallet для подключения", reply_markup=mk_b.as_markup()
#         )


# @top_up_router.message(Command("transaction"))
# async def send_transaction(message: Message):
#     connector = get_connector(message.chat.id)
#     connected = await connector.restore_connection()
#     if not connected:
#         await message.answer("Сначала подключите wallet в telegram!")
#         return
#
#     rub_to_ton_rate = get_ton_exchange_rate()
#     amount_in_rubles = 5.5514  # this is current 0.01 TON rate
#     amount_in_ton = rub_to_ton(amount_in_rubles, rub_to_ton_rate)
#
#     logger.info(amount_in_ton, "amount_in_ton")
#
#     transaction = {
#         "valid_until": int(time.time() + 3600),
#         "messages": [
#             get_comment_message(
#                 destination_address=settings.bot_wallet_address,
#                 amount=int(amount_in_ton * 10**9),
#                 comment="Here would be a good comment to u my friend!",
#             )
#         ],
#     }

#     await message.answer(text="Подтвердите транзакцию в приложении wallet в telegram!")
#     try:
#         await asyncio.wait_for(connector.send_transaction(transaction=transaction), 60)
#     except asyncio.TimeoutError:
#         await message.answer(
#             text='Время вышло. \nДля повторного проведения транзакции нажмите кнопку "старт"'
#         )
#     except pytonconnect.exceptions.UserRejectsError:
#         await message.answer(text="You rejected the transaction!")
#     except Exception as e:
#         await message.answer(text=f"Unknown error: {e}")
#
#
# @top_up_router.callback_query(lambda call: True)
# async def main_callback_handler(call: CallbackQuery):
#     await call.answer()
#     message = call.message
#     data = call.data
#     if data == "start":
#         await command_start_handler(message)
#     elif data == "send_tr":
#         await send_transaction(message)
#     elif data == "disconnect":
#         await disconnect_wallet(message)
#     else:
#         data = data.split(":")
#         if data[0] == "connect":
#             await connect_wallet(message, data[1])
