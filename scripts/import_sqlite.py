"""Eski örnek veritabanını boş PostgreSQL şemasına tek işlemde aktarır."""
import json
import sqlite3
import sys
from contextlib import closing
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text, inspect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import get_engine

TABLES = {
    'raw_materials': ['id', 'name', 'category', 'unit', 'current_stock', 'min_alert', 'cost'],
    'products': ['id', 'cat_id', 'name', 'price', 'type'],
    'dining_tables': ['id', 'name', 'category'],
    'staff': ['id', 'name', 'role', 'pin'],
    'orders': ['order_id', 'timestamp', 'table_id', 'table_name', 'weekday', 'weather', 'temperature', 'staff_name', 'staff_pin', 'payment_method', 'total_amount'],
    'order_items': ['id', 'order_id', 'product_id', 'product_name', 'quantity', 'unit_price'],
}

def import_data(source=None, engine=None):
    """Kaynağı değiştirmez; hedef doluysa hiçbir veri yazmadan durur."""
    source = Path(source) if source else ROOT / 'data' / 'sample_cafe.db'
    engine = engine or get_engine()
    with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as old:
        old.row_factory = sqlite3.Row
        old.execute('BEGIN')
        categories = json.loads((ROOT / 'data' / 'sample_cafe_data.json').read_text(encoding='utf-8'))['categories']
        with engine.begin() as new:
            for table in [*TABLES, 'categories', 'open_tabs']:
                if new.execute(text(f'SELECT EXISTS (SELECT 1 FROM {table})')).scalar():
                    raise RuntimeError(f'Hedef tablo boş değil: {table}; aktarım yapılmadı.')
            new.execute(text('INSERT INTO categories (id, name, display_order) VALUES (:id, :name, :display_order)'), categories)
            for table, columns in TABLES.items():
                names = ', '.join(columns)
                params = ', '.join(':' + c for c in columns)
                insert = text(f'INSERT INTO {table} ({names}) VALUES ({params})')
                cursor = old.execute(f'SELECT {names} FROM {table}')
                while rows := cursor.fetchmany(2000):
                    new.execute(insert, [dict(row) for row in rows])
                source_count = old.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                target_count = new.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
                if source_count != target_count:
                    raise RuntimeError(f'{table}: kayıt sayıları eşleşmiyor.')
                print(f'{table}: {target_count} kayıt doğrulandı')
            source_total = Decimal(str(old.execute('SELECT COALESCE(SUM(total_amount), 0) FROM orders').fetchone()[0]))
            target_total = new.execute(text('SELECT COALESCE(SUM(total_amount), 0) FROM orders')).scalar()
            if source_total.quantize(Decimal('.01')) != target_total:
                raise RuntimeError('Aktarılan ciro kaynakla eşleşmiyor.')
            new.execute(text("SELECT setval(pg_get_serial_sequence('order_items', 'id'), COALESCE((SELECT MAX(id) FROM order_items), 1), EXISTS(SELECT 1 FROM order_items))"))
            if inspect(new).has_table('stock_movements'):
                new.execute(text("""INSERT INTO stock_movements(material_id,kind,quantity,balance_after,unit,reason)
                    SELECT id,'opening',current_stock,current_stock,unit,'Örnek veri açılış bakiyesi'
                    FROM raw_materials WHERE current_stock>0"""))
            print('Ciro toplamı doğrulandı; işlem tamamlandı.')

if __name__ == '__main__':
    import_data()
