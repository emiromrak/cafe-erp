"""
CafeERP - Yapay Zeka & Karar Destek API Rotaları (FastAPI Endpoints)
Web dashboard, tablet POS ve mobil garson arayüzünün doğrudan tüketebileceği
RESTful servisleri sunar.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.ai.decision_engine import decision_engine

router = APIRouter(prefix="/api/ai", tags=["AI & Decision Engine"])

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    intent: str
    title: str
    text: str
    quick_replies: List[str]

@router.get("/sales-summary", summary="Günlük Satış & Kasa Özeti")
def get_sales_summary(date: Optional[str] = Query(None, description="Tarih formatı: YYYY-MM-DD")):
    """Gerçekleşen günlük ciro, fiş sayısı, ortalama sepet ve en çok satan ürünleri döner."""
    return decision_engine.get_sales_summary(target_date=date)

@router.get("/traffic-forecast", summary="Günün Yoğunluk ve Talep Tahmini")
def get_traffic_forecast():
    """Canlı hava durumu ve LightGBM modelini harmanlayarak saatlik yoğunluk ve pik saati döner."""
    return decision_engine.get_traffic_and_forecast()

@router.get("/stock-status", summary="Stok Tükenme ve Kritik Hammadde Uyarısı")
def get_stock_status():
    """Depo stoklarını ve yoğunluk tahminine göre hammaddelerin kaçta tükeneceğini (Burn-Rate) döner."""
    return decision_engine.get_stock_and_burn_rate()

@router.get("/daily-brief", summary="Günlük Yönetici Brifingi")
def get_daily_brief():
    """Kafe sahibi için satış, hava durumu, yoğunluk ve stok uyarılarını birleştiren tam özet döner."""
    return decision_engine.get_daily_brief()

@router.post("/query", response_model=QueryResponse, summary="Serbest Türkçe Soru Çözümleyici")
def ask_question(payload: QueryRequest):
    """
    Kullanıcının yazdığı serbest Türkçe soruyu ('bugün ne kadar satış yapıldı', 'yoğunluk nedir')
    çözümleyip doğrudan cevabı döner.
    """
    return decision_engine.resolve_nl_query(payload.query)
