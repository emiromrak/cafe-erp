"""Menü ve açık adisyonlardan türetilen masa durumları."""
from fastapi import APIRouter
from sqlalchemy import text
from app.ai.decision_engine import _engine

router = APIRouter(prefix='/api', tags=['Menü ve masalar'])

@router.get('/categories')
def categories():
    with _engine().connect() as conn:
        return [dict(r) for r in conn.execute(text('SELECT id, name, display_order FROM categories ORDER BY display_order, id')).mappings()]

@router.get('/products')
def products(category_id: str | None = None):
    with _engine().connect() as conn:
        sql = 'SELECT id, name, cat_id AS category_id, price, type FROM products'
        params = {}
        if category_id is not None:
            sql += ' WHERE cat_id = :category_id'
            params['category_id'] = category_id
        return [dict(r) for r in conn.execute(text(sql + ' ORDER BY name, id'), params).mappings()]

@router.get('/tables')
def tables():
    with _engine().connect() as conn:
        return [dict(r) for r in conn.execute(text('''
            SELECT t.id, t.name, t.category AS area,
                   CASE WHEN EXISTS (SELECT 1 FROM open_tabs a WHERE a.table_id = t.id AND a.closed_at IS NULL)
                   THEN 'occupied' ELSE 'empty' END AS status
            FROM dining_tables t ORDER BY t.name, t.id
        ''')).mappings()]
