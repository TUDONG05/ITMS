from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.internship_members import router as internship_members_router
from app.api.v1.internships import router as internships_router
from app.api.v1.me import router as me_router
from app.api.v1.profile import router as profile_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(me_router)
api_router.include_router(profile_router)
api_router.include_router(users_router)
api_router.include_router(internships_router)
api_router.include_router(internship_members_router)
