"""Örnek JSON reçetelerini boş ürün reçetelerine aktarır; mevcutlarını değiştirmez."""
import json
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import get_engine
from app.stock_service import replace_recipe
from app.api.stock_routes import Recipe


def import_recipes(source=None, engine=None):
    """Tüm aktarımı atomik yapar; farklı kafenin ürün/hammadde kimliğini uydurmaz."""
    source = Path(source) if source else ROOT / 'data' / 'sample_cafe_data.json'
    recipes = json.loads(source.read_text(encoding='utf-8'), parse_float=Decimal)['recipes']
    owns_engine = engine is None
    engine = engine if engine is not None else get_engine()
    imported = skipped = 0
    try:
        with engine.begin() as conn:
            # Birden çok ürünü değiştirmeden önce sabit sırayla ürünleri kilitle.
            for product_id in sorted(recipes):
                if not conn.execute(text('SELECT id FROM products WHERE id=:id FOR UPDATE'), {'id':product_id}).first():
                    raise ValueError(f'Örnek reçetenin ürünü bulunamadı: {product_id}')
            for product_id, lines in sorted(recipes.items()):
                if conn.execute(text('SELECT 1 FROM product_recipes WHERE product_id=:id'), {'id':product_id}).first():
                    skipped += 1
                    continue
                body = Recipe.model_validate({'expected_version':0, 'reason':'Örnek JSON reçete aktarımı',
                    'lines':[{'material_id':line['rm_id'],'quantity':str(line['qty'])} for line in lines]})
                replace_recipe(conn,product_id,body.model_dump(mode='json'))
                imported += 1
    finally:
        if owns_engine:
            engine.dispose()
    return {'imported':imported,'preserved':skipped}


if __name__ == '__main__':
    print(import_recipes())
