# ==========================================
# Main FastAPI Application
# ==========================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .build_router import router as build_router


# ==========================================
# Create FastAPI App
# ==========================================

app = FastAPI(
    title="PC Builder API",
    description="Simple API for PC component/product data",
    version="1.0.0"
)


# ==========================================
# CORS Configuration
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==========================================
# Include Routers
# ==========================================

# Existing product APIs
app.include_router(router)

# AI PC Builder API
app.include_router(build_router)


# ==========================================
# Root Endpoint
# ==========================================

@app.get("/")
def root():
    return {
        "success": True,
        "message": "PC Builder API is running"
    }