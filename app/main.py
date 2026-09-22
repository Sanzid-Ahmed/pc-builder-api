# ==========================================
# Main FastAPI Application
# ==========================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .build_router import router as build_router
from .user_router import router as user_router
from .build_limit_router import router as build_limit_router

from .order_router import router as order_router


# ==========================================
# Create FastAPI App
# ==========================================

app = FastAPI(
    title="PC Builder API",
    description="API for PC component/product data, PC building, user management, and build limits",
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

# PC Builder API
app.include_router(build_router)

# User API
app.include_router(user_router)

# Build Limit API
app.include_router(build_limit_router)

# Order API
app.include_router(order_router)


# ==========================================
# Root Endpoint
# ==========================================

@app.get("/")
def root():
    return {
        "success": True,
        "message": "PC Builder API is running"
    }