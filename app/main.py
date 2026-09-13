# ==========================================
# Main FastAPI Application
# ==========================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router


# ==========================================
# Create FastAPI Application
# ==========================================

app = FastAPI(
    title="PC Builder API",
    description="Simple API for PC component/product data",
    version="1.0.0"
)


# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=False,

    allow_methods=["*"],

    allow_headers=["*"]
)


# ==========================================
# Add Routes
# ==========================================

app.include_router(router)


# ==========================================
# Root Endpoint
# ==========================================

@app.get("/")
def root():

    return {
        "success": True,
        "message": "PC Builder API is running"
    }