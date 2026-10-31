"""Reçete ve stok API'si; miktarlar kesin ondalık metin olarak taşınır."""
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from fastapi.encoders import jsonable_encoder
from pydantic import Field, StringConstraints
from sqlalchemy import text

from app.ai import decision_engine
from app.api.tab_routes import Request, Key, Identifier, Versioned
from app import stock_service
from app.auth import User
from app.transactions import fail, row

router = APIRouter(prefix='/api', tags=['Reçete ve stok'])
Quantity = Annotated[Decimal, Field(gt=0, lt=Decimal('100000000000000'), max_digits=20, decimal_places=6, allow_inf_nan=False)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class RecipeLine(Request):
    """Hammaddenin kayıtlı biriminde bir ürün başına miktar."""
    material_id: Identifier
    quantity: Quantity


class Recipe(Versioned):
    """Bütün reçeteyi yeni sürümle değiştirir; geçmişi korur."""
    lines: Annotated[list[RecipeLine], Field(min_length=1, max_length=100)]
    reason: Reason


class Movement(Request):
    """Pozitif miktar gönderilir; stok etkisinin yönünü işlem türü belirler."""
    kind: Literal['receipt','return','waste','staff','complimentary']
    quantity: Quantity
    unit: Annotated[str, StringConstraints(strip_whitespace=True,min_length=1,max_length=30)]
    reason: Reason


@router.get('/inventory/materials', summary='Gerçek stok ve kritik eşikler')
def materials():
    with decision_engine._engine().connect() as conn:
        result = [dict(r) for r in conn.execute(text('''SELECT *,current_stock<=min_alert AS is_critical
            FROM raw_materials ORDER BY name,id''')).mappings()]
        return jsonable_encoder(result, custom_encoder={Decimal:str})


@router.get('/inventory/movements', summary='Stok hareket defteri ve üretim iptal durumu')
def movements(material_id: str | None = None, after_id: Annotated[int, Query(ge=0,le=9223372036854775807)] = 0,
              limit: Annotated[int, Query(ge=1,le=200)] = 100):
    with decision_engine._engine().connect() as conn:
        result = [dict(r) for r in conn.execute(text('''SELECT s.*,i.disposition FROM stock_movements s
            LEFT JOIN item_materials i ON i.item_id=s.item_id AND i.material_id=s.material_id
            WHERE s.id>:after AND (CAST(:material AS text) IS NULL OR s.material_id=:material)
            ORDER BY s.id LIMIT :limit'''), {'after':after_id,'material':material_id,'limit':limit}).mappings()]
        return jsonable_encoder(result, custom_encoder={Decimal:str})


@router.post('/inventory/materials/{material_id}/movements', summary='Giriş, iade veya tüketim kaydet')
def record_movement(material_id: str, body: Movement, key: Key, user: User):
    return stock_service.execute(decision_engine._engine(), key, 'movement', body.model_dump(mode='json'), material_id, actor=user)


@router.get('/recipes/{product_id}', summary='Güncel ürün reçetesi')
def get_recipe(product_id: str):
    with decision_engine._engine().begin() as conn:
        if row(conn, 'SELECT id FROM products WHERE id=:id FOR SHARE', id=product_id) is None:
            fail('Ürün bulunamadı.',404)
        return jsonable_encoder(stock_service.recipe_snapshot(conn,product_id),custom_encoder={Decimal:str})


@router.put('/recipes/{product_id}', summary='Reçeteyi sürümleyerek kaydet')
def save_recipe(product_id: str, body: Recipe, key: Key, user: User):
    return stock_service.execute(decision_engine._engine(),key,'recipe',body.model_dump(mode='json'),product_id,actor=user)
