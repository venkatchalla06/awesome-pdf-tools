from fastapi import APIRouter
from app.api.v1 import auth, files, jobs
from app.api.v1.tools import merge
from app.api.v1.tools.all_tools import router as tools_router

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(files.router)
api_router.include_router(jobs.router)
api_router.include_router(merge.router)
api_router.include_router(tools_router)
