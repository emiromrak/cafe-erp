"""Reçete ve gerçek stok hareketleri; tüm miktarlar Decimal/NUMERIC kullanır."""
import json
from decimal import Decimal

from sqlalchemy import text
from app.transactions import fail, row, run_idempotent

MAX_QUANTITY = Decimal('99999999999999.999999')

# Mevcut modelin eğitildiği ürün grupları; reçete miktarı burada tanımlanmaz.
FORECAST_GROUPS = {
    'predicted_tea_glasses': ('prod_tea_glass',),
    'predicted_toasts': ('prod_toast_cheese','prod_toast_mixed'),
    'predicted_hot_coffee': ('prod_latte','prod_flat_white','prod_americano','prod_filter','prod_turkish_coffee'),
    'predicted_cold_drinks': ('prod_cold_brew','prod_iced_latte','prod_soda','prod_ayran'),
}


def forecast_recipe_mix(conn):
    """Grup tahminini son aktif 30 günün ürün payıyla SQL reçetelerine dağıtır.

    Geçmişi olmayan grupta eşit pay varsayımı açıkça bildirilir. Eksik reçeteli
    grubun tüketimi tahmin edilmez; eksiklik stok yeterliymiş gibi gizlenmez.
    """
    products = {r['id'] for r in conn.execute(text('SELECT id FROM products')).mappings()}
    lines = [dict(r) for r in conn.execute(text('''SELECT r.product_id,r.material_id,r.quantity,
        m.name,m.unit FROM recipe_lines r JOIN raw_materials m ON m.id=r.material_id''')).mappings()]
    counts = dict(conn.execute(text('''SELECT i.product_id,SUM(i.quantity) FROM order_items i
        JOIN orders o ON o.order_id=i.order_id WHERE substr(o.timestamp,1,10) >=
        ((SELECT MAX(substr(timestamp,1,10))::date FROM orders) - interval '30 days')::date::text
        GROUP BY i.product_id''')).all())
    result, warnings = {}, []
    for key, ids in FORECAST_GROUPS.items():
        present = sorted(products.intersection(ids))
        if not present:
            continue
        missing = [p for p in present if not any(r['product_id']==p for r in lines)]
        if missing:
            warnings.append({'group':key,'reason':'missing_recipes','products':missing})
            continue
        total = sum(counts.get(p,0) for p in present)
        if not total:
            warnings.append({'group':key,'reason':'equal_mix_no_history','products':present})
        result[key] = []
        for line in lines:
            if line['product_id'] in present:
                weight = Decimal(counts.get(line['product_id'],0))/Decimal(total) if total else Decimal(1)/len(present)
                result[key].append({**line,'quantity':line['quantity']*weight})
    unmodeled = sorted(products.difference(p for ids in FORECAST_GROUPS.values() for p in ids))
    if unmodeled:
        warnings.append({'reason':'products_outside_forecast_model','products':unmodeled})
    return result, warnings


def material_snapshot(conn, material_id):
    """Bakiyeyi ve kritik eşik durumunu tek sorguda okur."""
    result = row(conn, '''SELECT *,current_stock <= min_alert AS is_critical
        FROM raw_materials WHERE id=:id''', id=material_id)
    if result is None:
        fail('Hammadde bulunamadı.', 404)
    return result


def recipe_snapshot(conn, product_id):
    """Reçete sürümünü ve bir ürün başına kesin tüketimi okur."""
    result = row(conn, 'SELECT * FROM product_recipes WHERE product_id=:id', id=product_id)
    if result is None:
        if row(conn, 'SELECT id FROM products WHERE id=:id', id=product_id) is None:
            fail('Ürün bulunamadı.', 404)
        result = {'product_id': product_id, 'version': 0, 'updated_at': None}
    result['lines'] = [dict(r) for r in conn.execute(text('''SELECT l.material_id,l.quantity,
        m.unit,m.name AS material_name FROM recipe_lines l JOIN raw_materials m ON m.id=l.material_id
        WHERE l.product_id=:id ORDER BY l.material_id'''), {'id': product_id}).mappings()]
    return result


def replace_recipe(conn, product_id, payload):
    """Ürün kilidi altında reçeteyi sürümleyerek değiştirir; boş reçete kabul etmez."""
    if row(conn, 'SELECT id FROM products WHERE id=:id FOR UPDATE', id=product_id) is None:
        fail('Ürün bulunamadı.', 404)
    current = recipe_snapshot(conn, product_id)
    if current['version'] != payload['expected_version']:
        fail('Reçete değişmiş; güncel sürümü okuyun.')
    lines = payload['lines']
    ids = [line['material_id'] for line in lines]
    if len(ids) != len(set(ids)):
        fail('Reçetede aynı hammadde birden fazla yazılamaz.', 422)
    # Sabit kilit sırası iki farklı reçetenin aynı stoklarla kilitlenmesini önler.
    for material_id in sorted(ids):
        if row(conn, 'SELECT id FROM raw_materials WHERE id=:id FOR SHARE', id=material_id) is None:
            fail('Reçetedeki hammadde bulunamadı.', 404)
    version = current['version'] + 1
    conn.execute(text('''INSERT INTO product_recipes(product_id,version) VALUES (:id,:v)
        ON CONFLICT(product_id) DO UPDATE SET version=EXCLUDED.version,updated_at=now()'''), {'id': product_id,'v': version})
    conn.execute(text('DELETE FROM recipe_lines WHERE product_id=:id'), {'id': product_id})
    for line in lines:
        conn.execute(text('INSERT INTO recipe_lines VALUES (:id,:material,:quantity)'),
                     {'id':product_id,'material':line['material_id'],'quantity':Decimal(line['quantity'])})
    conn.execute(text('INSERT INTO recipe_history(product_id,version,lines,reason) VALUES (:id,:v,CAST(:lines AS jsonb),:reason)'),
                 {'id': product_id,'v':version,'lines':json.dumps(lines),'reason':payload['reason']})
    return recipe_snapshot(conn, product_id)


def change_balance(conn, material, quantity, kind, reason, item_id=None):
    """Kilitli hammaddenin bakiyesini ve defter hareketini birlikte yazar."""
    balance = material['current_stock'] + quantity
    if balance < 0:
        fail(f"Yetersiz stok: {material['name']} ({material['current_stock']} {material['unit']}).")
    if balance > MAX_QUANTITY:
        fail('Stok miktarı desteklenen sınırı aşıyor.', 422)
    conn.execute(text('UPDATE raw_materials SET current_stock=:qty WHERE id=:id'), {'id':material['id'],'qty':balance})
    conn.execute(text('''INSERT INTO stock_movements(material_id,item_id,kind,quantity,balance_after,unit,reason)
        VALUES (:id,:item,:kind,:qty,:balance,:unit,:reason)'''),
        {'id':material['id'],'item':item_id,'kind':kind,'qty':quantity,'balance':balance,'unit':material['unit'],'reason':reason})


def consume_item(conn, item):
    """Hazırlık başladığında reçeteyi kopyalar ve stoğu bir kez tüketir.

    Kilit sırası: adisyon → ürün → sıralı hammaddeler. Reçete değişse bile
    mevcut üretimin miktar ve birimleri item_materials içinde korunur.
    """
    conn.execute(text('SELECT id FROM products WHERE id=:id FOR SHARE'), {'id':item['product_id']})
    recipe = recipe_snapshot(conn, item['product_id'])
    if not recipe['lines']:
        fail('Ürünün reçetesi tanımlı değil; hazırlık başlatılamaz.')
    if row(conn, 'SELECT item_id FROM item_materials WHERE item_id=:id', id=item['id']):
        fail('Kalemin stok tüketimi zaten kaydedilmiş.')
    for line in recipe['lines']:
        material = row(conn, 'SELECT * FROM raw_materials WHERE id=:id FOR UPDATE', id=line['material_id'])
        quantity = line['quantity'] * item['quantity']
        if quantity > MAX_QUANTITY:
            fail('Reçete tüketimi desteklenen sınırı aşıyor.', 422)
        change_balance(conn, material, -quantity, 'consume', 'Ürün hazırlığı', item['id'])
        conn.execute(text('''INSERT INTO item_materials
            (item_id,material_id,recipe_version,unit,quantity_per_unit,quantity)
            VALUES (:item,:material,:version,:unit,:per,:quantity)'''),
            {'item':item['id'],'material':material['id'],'version':recipe['version'],
             'unit':material['unit'],'per':line['quantity'],'quantity':quantity})


def mark_waste(conn, item_id):
    """Hazırlanmış ürün iptalinde zaten tüketilmiş stoğu ikinci kez düşmez."""
    conn.execute(text("UPDATE item_materials SET disposition='waste' WHERE item_id=:id"), {'id':item_id})


def execute(engine, key, operation, payload, resource_id):
    """Reçete/manuel stok yazmalarını adisyonlarla ortak tekrar korumasına alır."""
    def action(conn):
        if operation == 'recipe':
            return replace_recipe(conn, resource_id, payload)
        material = row(conn, 'SELECT * FROM raw_materials WHERE id=:id FOR UPDATE', id=resource_id)
        if material is None:
            fail('Hammadde bulunamadı.', 404)
        if payload['unit'] != material['unit']:
            fail('Miktar hammaddenin kayıtlı biriminde gönderilmeli.', 422)
        quantity = Decimal(payload['quantity'])
        if payload['kind'] in ('waste','staff','complimentary'):
            quantity = -quantity
        change_balance(conn, material, quantity, payload['kind'], payload['reason'])
        return material_snapshot(conn, resource_id)
    return run_idempotent(engine, key, {'operation':operation,'resource_id':resource_id,'payload':payload}, action)
