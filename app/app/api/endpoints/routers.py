from fastapi import APIRouter

from app.core.config import settings
from app.api.endpoints.crypto_bot import router as crypto_bot_router


api_router = APIRouter()

api_router.include_router(crypto_bot_router)
