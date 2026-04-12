import aiohttp
import loguru

from app.core.config import settings


class CryptoBotAPIService:

    def __init__(
        self,
        base_url: str = settings.crypto_bot_api_base_url,
        api_token: str = settings.crypto_bot_api_token,
    ):
        self.base_url = base_url
        self.__api_token = api_token

    async def create_invoice(
            self,
            amount: float,
            description: str,
            asset: str = "USDT",
            payload: dict = {},
    ):
        method = "createInvoice"
        url = f"{self.base_url}{method}"

        headers = {"Crypto-Pay-API-Token": self.__api_token}

        data = {
            "asset": asset,
            "amount": amount,
            "description": description,
            "payload": payload,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                return await resp.json()

    async def get_invoices(self):
        method = "getInvoices"
        url = f"{self.base_url}{method}"

        headers = {"Crypto-Pay-API-Token": self.__api_token}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                return await resp.json()