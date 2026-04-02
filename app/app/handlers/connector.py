from pytonconnect import TonConnect

from app.core.config import settings
from app.handlers.tc_storage import TcStorage


def get_connector(chat_id: int):
    return TonConnect(settings.manifest_url, storage=TcStorage(chat_id))
