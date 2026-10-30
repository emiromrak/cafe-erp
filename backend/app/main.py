"""
CafeERP - Ana FastAPI Uygulaması
"""

import sys
from pathlib import Path

# Backend dizinini sys.path'e ekle (nereden çalıştırılırsa çalıştırılsın iç importlar bozulmaz)
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.ai.predictor import ForecastUnavailableError
from app.api.catalog_routes import router as catalog_router
from app.api.tab_routes import router as tab_router
from app.api.stock_routes import router as stock_router

try:
    from app.api.ai_routes import router as ai_router
except ImportError:
    from backend.app.api.ai_routes import router as ai_router

app = FastAPI(
    title="CafeERP Backend API",
    description="Kafe Yönetim, POS ve Yapay Zeka Karar Destek API Servisi",
    version="1.0.0"
)

# CORS ayarları (Next.js PWA ve tablet arayüzleri için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)

# API Rotaları
app.include_router(ai_router)
app.include_router(catalog_router)
app.include_router(tab_router)
app.include_router(stock_router)

@app.exception_handler(ForecastUnavailableError)
async def forecast_unavailable_handler(request, exc):
    """Model eksikliğini sahte tahmin üretmeden istemciye bildirir."""
    return JSONResponse(status_code=503, content={"detail": str(exc)})

@app.get("/")
def root():
    return {
        "status": "online",
        "app": "CafeERP Backend",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
