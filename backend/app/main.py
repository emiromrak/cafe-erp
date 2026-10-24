"""
CafeERP - Ana FastAPI Uygulaması
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.ai_routes import router as ai_router

app = FastAPI(
    title="CafeERP Backend API",
    description="Kafe Yönetim, POS ve Yapay Zeka Karar Destek API Servisi",
    version="1.0.0"
)

# CORS ayarları (Next.js PWA ve tablet arayüzleri için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Rotaları
app.include_router(ai_router)

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
