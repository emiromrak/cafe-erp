"""İşlemler için ortak hata, sorgu ve atomik tekrar koruması."""
import hashlib
import json
from decimal import Decimal

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text


def fail(message, status=409):
    """İş kuralı ihlalini istemcinin düzeltebileceği hataya dönüştürür."""
    raise HTTPException(status_code=status, detail=message)


def row(conn, sql, **params):
    """Parametreli sorgunun tek kaydını sözlük olarak okur."""
    result = conn.execute(text(sql), params).mappings().first()
    return dict(result) if result is not None else None


def run_idempotent(engine, key, request, action, actor=None):
    """Başarılı yanıtı iş verileriyle tek transaction içinde saklar.

    Stok miktarları JSON'da metin olarak taşınır; float yuvarlaması yapılmaz.
    Başarısız istekler anahtarı tüketmez. Anahtar tüm yazma uçları için ortaktır.
    """
    if actor is not None:
        request = {**request, 'actor_id': actor['id']}
    digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    lock_id = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big', signed=True)
    with engine.begin() as conn:
        if actor is not None:
            current = row(conn, 'SELECT is_active,version FROM staff_accounts WHERE id=:id FOR SHARE', id=actor['id'])
            if not current or not current['is_active'] or current['version'] != actor['version']:
                fail('Personel oturumu değişmiş. Tekrar giriş yapın.', 401)
        conn.execute(text('SELECT pg_advisory_xact_lock(:id)'), {'id': lock_id})
        previous = row(conn, 'SELECT * FROM api_requests WHERE key=:key', key=key)
        if previous:
            if previous['request_hash'] != digest:
                fail('Idempotency-Key farklı bir istek için kullanılmış.')
            return previous['response']
        result = jsonable_encoder(action(conn), custom_encoder={Decimal: str})
        if actor is not None:
            from app.auth import audit
            audit(conn, actor['id'], request['operation'],
                  request.get('tab_id') or request.get('resource_id') or result.get('id'), key)
        conn.execute(text('''INSERT INTO api_requests (key,request_hash,response)
            VALUES (:key,:hash,CAST(:response AS jsonb))'''),
            {'key': key, 'hash': digest, 'response': json.dumps(result, ensure_ascii=False)})
        return result
