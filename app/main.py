from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import engine
from app.models import base

# Create database tables
base.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PDF Toolkit API",
    description="Complete PDF processing platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "PDF Toolkit API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}