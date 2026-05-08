import re

import loguru
from app.models.withdrawal_request import CryptoNetworkType


class ValidateWalletAddress:
    def __init__(self, address: str, network: CryptoNetworkType):
        self.address = address
        self.network = network

    @staticmethod
    def validate_bep20(address: str) -> bool:
        return bool(re.fullmatch(r'0x[a-fA-F0-9]{40}', address))

    @staticmethod
    def validate_solana(address: str) -> bool:
        return 32 <= len(address) <= 44 and bool(re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]+', address))

    @staticmethod
    def validate_ton(address: str) -> bool:
        if address.startswith('0:'):
            return bool(re.fullmatch(r'0:[0-9a-fA-F]+', address))

        return 20 <= len(address) <= 90 and bool(re.fullmatch(r'[A-Za-z0-9_\-]+', address))

    def __call__(self) -> bool:
        if self.network == CryptoNetworkType.BEP20:
            return self.validate_bep20(self.address)
        if self.network == CryptoNetworkType.SOLANA:
            return self.validate_solana(self.address)
        if self.network == CryptoNetworkType.TON:
            return self.validate_ton(self.address)

        return False

