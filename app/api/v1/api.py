from fastapi import APIRouter
from .endpoints import files, jobs, tools

api_router = APIRouter()

api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])