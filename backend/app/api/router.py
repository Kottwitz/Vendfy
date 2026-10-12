from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.clients import router as clients_router
from app.api.routes.companies import router as companies_router
from app.api.routes.health import router as health_router
from app.api.routes.quotes import router as quotes_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(clients_router, tags=["clients"])
api_router.include_router(companies_router, tags=["companies"])
api_router.include_router(quotes_router, tags=["quotes"])
