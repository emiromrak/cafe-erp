"""Adisyon işlemleri: tam sayı para, satır kilitleri ve atomik tekrar koruması."""
import json
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from app.transactions import fail, row, run_idempotent
from app import stock_service

MAX_CENTS = 999999999999  # Mevcut NUMERIC(12,2) satış alanıyla uyumlu sınır.


def snapshot(conn, tab_id):
    """Kilit altındaki adisyonun tutarını yalnızca aktif kalemlerden hesaplar."""
    tab = row(conn, 'SELECT * FROM open_tabs WHERE id=:id', id=tab_id)
    if tab is None:
        fail('Adisyon bulunamadı.', 404)
    tab['items'] = [dict(r) for r in conn.execute(text(
        'SELECT * FROM tab_items WHERE tab_id=:id ORDER BY id'), {'id': tab_id}).mappings()]
    tab['total_cents'] = sum(i['quantity'] * i['unit_price_cents'] for i in tab['items'] if i['status'] != 'cancelled')
    tab['payment'] = row(conn, 'SELECT * FROM tab_payments WHERE tab_id=:id', id=tab_id)
    return tab


def read_tab(engine, tab_id):
    """Birden çok sorguyu aynı adisyon kilidi altında tutarlı biçimde okur."""
    with engine.begin() as conn:
        if row(conn, 'SELECT id FROM open_tabs WHERE id=:id FOR SHARE', id=tab_id) is None:
            fail('Adisyon bulunamadı.', 404)
        return snapshot(conn, tab_id)


def record_event(conn, tab_id, event_type, data):
    """Değişiklik geçmişini iş işlemiyle aynı transaction içinde saklar."""
    conn.execute(text('''INSERT INTO tab_events (tab_id,event_type,data)
        VALUES (:id,:type,CAST(:data AS jsonb))'''),
        {'id': tab_id, 'type': event_type, 'data': json.dumps(data, ensure_ascii=False)})


def clear_ready(engine, key, item_ids, actor=None):
    """Hazır kartlarını kalıcı gizler; adisyon sürümü, durum, ödeme ve stok değişmez."""
    ids=sorted(set(item_ids))
    def action(conn):
        # Diğer adisyon işlemleriyle aynı kilit; çok masada kilit sırası sabittir.
        tabs=conn.execute(text('''SELECT id FROM open_tabs WHERE closed_at IS NULL
            AND id IN (SELECT tab_id FROM tab_items WHERE id=ANY(:ids))
            ORDER BY id FOR UPDATE'''), {'ids':ids}).scalars().all()
        cleared=[]
        for tab_id in tabs:
            items=conn.execute(text('''SELECT i.id FROM tab_items i WHERE i.tab_id=:tab
                AND i.id=ANY(:ids) AND i.status='ready' AND NOT EXISTS (
                    SELECT 1 FROM tab_events e WHERE e.tab_id=i.tab_id
                    AND e.event_type='kitchen_cleared' AND e.data->>'item_id'=i.id::text)
                ORDER BY i.id'''), {'tab':tab_id,'ids':ids}).scalars().all()
            for item_id in items:
                record_event(conn,tab_id,'kitchen_cleared',{'item_id':item_id})
                cleared.append(item_id)
        return {'cleared_item_ids':cleared,'cleared_count':len(cleared)}
    return run_idempotent(engine,key,{'operation':'clear_ready','resource_id':'kitchen_ready','item_ids':ids},action,actor)


def execute(engine, key, operation, payload, tab_id=None, item_id=None, actor=None):
    """Tekrarları aynı yanıtla karşılar; hata halinde bütün yazmaları geri alır.

    Kilit sırası: istek anahtarı → masa (açılışta) veya adisyon → kalemler.
    Yanıt kaydı da aynı transaction içindedir; başarısız istek anahtarı tüketmez.
    """
    request = {'operation': operation, 'tab_id': tab_id, 'item_id': item_id, 'payload': payload}
    def action(conn):
        nonlocal tab_id
        if operation == 'open':
            table = row(conn, 'SELECT * FROM dining_tables WHERE id=:id FOR UPDATE', id=payload['table_id'])
            if table is None:
                fail('Masa bulunamadı.', 404)
            if row(conn, 'SELECT id FROM open_tabs WHERE table_id=:id AND closed_at IS NULL', id=table['id']):
                fail('Masanın zaten açık bir adisyonu var.')
            tab_id = conn.execute(text('INSERT INTO open_tabs (table_id) VALUES (:id) RETURNING id'), {'id': table['id']}).scalar_one()
            record_event(conn, tab_id, 'opened', payload)
        else:
            tab = row(conn, 'SELECT * FROM open_tabs WHERE id=:id FOR UPDATE', id=tab_id)
            if tab is None:
                fail('Adisyon bulunamadı.', 404)
            if tab['status'] != 'open':
                fail('Adisyon kapanmış; değiştirilemez.')
            if tab['version'] != payload['expected_version']:
                fail('Adisyon değişmiş; güncel sürümü okuyup tekrar deneyin.')
            changes = mutate(conn, operation, payload, tab, item_id, actor=actor)
            conn.execute(text('UPDATE open_tabs SET version=version+1 WHERE id=:id'), {'id': tab_id})
            record_event(conn, tab_id, operation, {
                **payload, 'item_id': item_id, 'version': tab['version'] + 1, **changes})

        result = snapshot(conn, tab_id)
        if result['total_cents'] > MAX_CENTS:
            fail('Adisyon tutarı desteklenen sınırı aşıyor.', 422)
        return result
    return run_idempotent(engine, key, request, action, actor)


def mutate(conn, operation, payload, tab, item_id, actor=None):
    """Kilitlenmiş açık adisyonda izin verilen durum geçişini uygular."""
    tab_id = tab['id']
    if operation == 'add_item':
        product = row(conn, 'SELECT * FROM products WHERE id=:id FOR SHARE', id=payload['product_id'])
        if product is None:
            fail('Ürün bulunamadı.', 404)
        price = product['price']
        if price is None or not price.is_finite() or price < 0 or not product['name']:
            fail('Ürünün satış fiyatı veya adı geçersiz.', 422)
        cents = price * 100
        if cents != cents.to_integral_value() or cents * payload['quantity'] > MAX_CENTS:
            fail('Ürün tutarı desteklenen sınırı aşıyor.', 422)
        # Gönderilmiş satırları ve farklı fiyat/ad kopyalarını değiştirmeden taslağı artır.
        draft = row(conn, '''SELECT * FROM tab_items WHERE tab_id=:tab AND product_id=:product
            AND status='draft' AND unit_price_cents=:price AND product_name=:name
            ORDER BY id LIMIT 1''', tab=tab_id, product=product['id'], price=int(cents), name=product['name'])
        if draft:
            quantity = draft['quantity'] + payload['quantity']
            if quantity > 10000 or quantity * int(cents) > MAX_CENTS:
                fail('Kalem miktarı veya tutarı desteklenen sınırı aşıyor.', 422)
            conn.execute(text('UPDATE tab_items SET quantity=:qty WHERE id=:id'), {'qty':quantity,'id':draft['id']})
            return {'item_id':draft['id'],'product_name':product['name'],'unit_price_cents':int(cents),
                    'quantity_before':draft['quantity'],'quantity_after':quantity}
        new_id = conn.execute(text('''INSERT INTO tab_items (tab_id,product_id,product_name,quantity,unit_price_cents)
            VALUES (:tab,:product,:name,:qty,:price) RETURNING id'''),
            {'tab': tab_id, 'product': product['id'], 'name': product['name'], 'qty': payload['quantity'], 'price': int(cents)}).scalar_one()
        return {'item_id': new_id, 'product_name': product['name'], 'unit_price_cents': int(cents)}
    elif operation in ('quantity', 'item_status', 'cancel_item', 'kitchen_cancel_item'):
        item = row(conn, 'SELECT * FROM tab_items WHERE id=:item AND tab_id=:tab', item=item_id, tab=tab_id)
        if item is None:
            fail('Adisyon kalemi bulunamadı.', 404)
        if operation in ('cancel_item','kitchen_cancel_item') and item['status'] in ('preparing','ready'):
            if actor is not None and actor['role'] not in ('admin','kitchen'):
                fail('Hazırlığı başlayan ürünü yalnızca mutfak veya yönetici iptal edebilir.')
        if operation == 'kitchen_cancel_item' and item['status'] not in ('sent','preparing','ready'):
            fail('Mutfaktan yalnızca gönderilmiş, hazırlanıyor veya hazır kalem iptal edilebilir.')
        if operation == 'quantity':
            if item['status'] != 'draft':
                fail('Yalnızca gönderilmemiş kalemin miktarı değiştirilebilir.')
            if payload['quantity'] == 0:
                # Taslak stok tüketmez; satırı kaldırırken önceki değeri olayda koru.
                conn.execute(text('DELETE FROM tab_items WHERE id=:id'), {'id':item_id})
                return {'removed':True,'quantity_before':item['quantity'],
                        'product_name':item['product_name'],'unit_price_cents':item['unit_price_cents']}
            if item['unit_price_cents'] * payload['quantity'] > MAX_CENTS:
                fail('Kalem tutarı desteklenen sınırı aşıyor.', 422)
            conn.execute(text('UPDATE tab_items SET quantity=:qty WHERE id=:id'), {'qty': payload['quantity'], 'id': item_id})
        else:
            status = 'cancelled' if operation in ('cancel_item','kitchen_cancel_item') else payload['status']
            allowed = {'sent': 'preparing', 'preparing': 'ready'}
            if item['status'] == 'cancelled' or (status != 'cancelled' and allowed.get(item['status']) != status):
                fail('Kalem için bu durum geçişine izin verilmiyor.')
            if status == 'preparing':
                stock_service.consume_item(conn, item)
            elif status == 'cancelled':
                stock_service.mark_waste(conn, item_id)
            conn.execute(text('UPDATE tab_items SET status=:status WHERE id=:id'), {'status': status, 'id': item_id})
    elif operation == 'submit':
        changed = conn.execute(text("UPDATE tab_items SET status='sent' WHERE tab_id=:id AND status='draft' RETURNING id"), {'id': tab_id}).all()
        if not changed:
            fail('Mutfağa gönderilecek yeni kalem yok.')
        return {'item_ids': [r[0] for r in changed]}
    elif operation == 'cancel_tab':
        if actor is not None and actor['role'] not in ('admin','kitchen'):
            if row(conn, "SELECT id FROM tab_items WHERE tab_id=:id AND status IN ('preparing','ready') LIMIT 1", id=tab_id):
                fail('Adisyonda hazırlığı başlayan ürün var. Önce mutfak veya yönetici bu ürünleri iptal etmeli.')
        conn.execute(text("""UPDATE item_materials SET disposition='waste'
            WHERE item_id IN (SELECT id FROM tab_items WHERE tab_id=:id AND status<>'cancelled')"""), {'id': tab_id})
        conn.execute(text("UPDATE tab_items SET status='cancelled' WHERE tab_id=:id AND status<>'cancelled'"), {'id': tab_id})
        conn.execute(text("UPDATE open_tabs SET status='cancelled',closed_at=now() WHERE id=:id"), {'id': tab_id})
    elif operation == 'pay':
        pay(conn, tab, payload)
    else:
        raise ValueError('Bilinmeyen adisyon işlemi.')
    return {}


def pay(conn, tab, payload):
    """Tek tahsilatı ve rapor satışını atomik olarak oluşturur; harici ödeme yapmaz."""
    current = snapshot(conn, tab['id'])
    active = [i for i in current['items'] if i['status'] != 'cancelled']
    total = current['total_cents']
    if not active or any(i['status'] != 'ready' for i in active):
        fail('Ödeme için bütün aktif kalemler hazır olmalı.')
    if total <= 0 or total > MAX_CENTS or payload['amount_cents'] != total:
        fail('Ödeme tutarı güncel adisyon tutarına eşit olmalı.')
    # Yerel satış tarihi, makinenin saat diliminden bağımsızdır; hava verisi uydurulmaz.
    now = datetime.now(ZoneInfo('Europe/Istanbul'))
    table = row(conn, 'SELECT name FROM dining_tables WHERE id=:id', id=tab['table_id'])
    order_id = 'TAB_' + uuid4().hex
    conn.execute(text('''INSERT INTO orders
        (order_id,timestamp,table_id,table_name,weekday,payment_method,total_amount)
        VALUES (:order,:time,:table,:name,:weekday,:method,:total)'''),
        {'order': order_id, 'time': now.strftime('%Y-%m-%d %H:%M:%S'), 'table': tab['table_id'],
         'name': table['name'], 'weekday': now.strftime('%A'),
         'method': {'cash': 'Nakit', 'card': 'Kredi Kartı'}[payload['method']], 'total': Decimal(total) / 100})
    for item in active:
        conn.execute(text('''INSERT INTO order_items (order_id,product_id,product_name,quantity,unit_price)
            VALUES (:order,:product,:name,:qty,:price)'''),
            {'order': order_id, 'product': item['product_id'], 'name': item['product_name'],
             'qty': item['quantity'], 'price': Decimal(item['unit_price_cents']) / 100})
    conn.execute(text('''INSERT INTO tab_payments (tab_id,order_id,amount_cents,method)
        VALUES (:tab,:order,:amount,:method)'''),
        {'tab': tab['id'], 'order': order_id, 'amount': total, 'method': payload['method']})
    conn.execute(text("UPDATE open_tabs SET status='paid',closed_at=now() WHERE id=:id"), {'id': tab['id']})
