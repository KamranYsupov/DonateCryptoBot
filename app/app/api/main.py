import uvicorn
from fastapi import FastAPI

from app.core.config import settings
from app.api.endpoints.routers import api_router
from app.core.container import Container

def create_app() -> FastAPI:
    fastapi_app = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None
    )
    fastapi_app.container = Container()
    fastapi_app.include_router(api_router, prefix=settings.api_prefix)

    return fastapi_app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app="app.api.main:app", host="0.0.0.0", reload=True)