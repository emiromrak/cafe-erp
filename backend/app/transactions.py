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


def run_idempotent(engine, key, request, action):
    """Başarılı yanıtı iş verileriyle tek transaction içinde saklar.

    Stok miktarları JSON'da metin olarak taşınır; float yuvarlaması yapılmaz.
    Başarısız istekler anahtarı tüketmez. Anahtar tüm yazma uçları için ortaktır.
    """
    digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    lock_id = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big', signed=True)
    with engine.begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(:id)'), {'id': lock_id})
        previous = row(conn, 'SELECT * FROM api_requests WHERE key=:key', key=key)
        if previous:
            if previous['request_hash'] != digest:
                fail('Idempotency-Key farklı bir istek için kullanılmış.')
            return previous['response']
        result = jsonable_encoder(action(conn), custom_encoder={Decimal: str})
        conn.execute(text('''INSERT INTO api_requests (key,request_hash,response)
            VALUES (:key,:hash,CAST(:response AS jsonb))'''),
            {'key': key, 'hash': digest, 'response': json.dumps(result, ensure_ascii=False)})
        return result
