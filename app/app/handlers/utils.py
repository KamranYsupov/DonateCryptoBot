import asyncio
import logging
import requests
from io import BytesIO

import qrcode
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pytoniq_core import Address

from app.handlers.connector import get_connector

logger = logging.getLogger(__file__)


async def connect_wallet(message: Message, wallet_name: str):
    connector = get_connector(message.chat.id)

    wallets_list = connector.get_wallets()
    wallet = None

    for w in wallets_list:
        if w["name"] == wallet_name:
            wallet = w

    if wallet is None:
        raise Exception(f"Unknown wallet: {wallet_name}")

    generated_url = await connector.connect(wallet)

    mk_b = InlineKeyboardBuilder()
    mk_b.button(text="Подключить", url=generated_url)

    img = qrcode.make(generated_url)
    stream = BytesIO()
    img.save(stream)
    file = BufferedInputFile(file=stream.getvalue(), filename="qrcode")

    await message.answer_photo(
        photo=file,
        caption="Подключите wallet в течение 3 минут",
        reply_markup=mk_b.as_markup(),
    )

    mk_b = InlineKeyboardBuilder()
    mk_b.button(text="Старт", callback_data="start")

    for i in range(1, 180):
        await asyncio.sleep(1)
        if connector.connected:
            if connector.account.address:
                wallet_address = connector.account.address
                wallet_address = Address(wallet_address).to_str(is_bounceable=False)
                await message.answer(
                    f"Вы подключены и ваш адрес <code>{wallet_address}</code>",
                    reply_markup=mk_b.as_markup(),
                )
                logger.info(f"Connected with address: {wallet_address}")
            return

    await message.answer(f"Время вышло!", reply_markup=mk_b.as_markup())


async def disconnect_wallet(message: Message):
    connector = get_connector(message.chat.id)
    await connector.restore_connection()
    await connector.disconnect()
    await message.answer("Вы успешно отключили wallet!")


def get_ton_exchange_rate():
    response = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=rub"
    )
    response.raise_for_status()
    data = response.json()
    return data["the-open-network"]["rub"]


def rub_to_ton(rubles, rate):
    return rubles / rate
