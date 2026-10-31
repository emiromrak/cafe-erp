"""Veritabanında doğrulanan personel oturumları ve rol sınırları."""
import hashlib
import os
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text

from app.ai import decision_engine
from app.transactions import row

COOKIE = 'cafeerp_session'
SESSION_SECONDS = 12 * 60 * 60
PUBLIC_FIELDS = 'id,username,name,role,is_active,version'


def allowed_origins():
    return [value.strip() for value in os.getenv(
        'CAFE_ALLOWED_ORIGINS',
        'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001'
    ).split(',') if value.strip()]


def secure_cookie():
    return os.getenv('CAFE_COOKIE_SECURE', 'false').lower() == 'true'


def hash_password(password, salt=None):
    """Rastgele tuzla scrypt; düz metin parola veya PIN saklanmaz."""
    if not 4 <= len(password) <= 128:
        raise ValueError('Parola 4–128 karakter olmalı.')
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                            n=131072, r=8, p=1, maxmem=256 * 1024 * 1024).hex()
    return f'scrypt${salt}${digest}'


def verify_password(password, encoded):
    try:
        algorithm, salt, digest = encoded.split('$')
        if algorithm != 'scrypt':
            return False
        actual = hash_password(password, salt).split('$')[2]
        return secrets.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def check_write(request: Request):
    """Özel başlık ve izinli Origin ile tarayıcı kaynaklı sahte yazmaları reddeder."""
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    if request.headers.get('X-CafeERP-Request') != '1':
        raise HTTPException(403, 'İstek güvenlik başlığı eksik.')
    origin = request.headers.get('origin')
    if origin is not None and origin not in allowed_origins():
        raise HTTPException(403, 'İstek kaynağına izin verilmiyor.')


def current_user(request: Request):
    token = request.cookies.get(COOKIE, '')
    if not token or len(token) > 200:
        raise HTTPException(401, 'Personel girişi gerekli.')
    with decision_engine._engine().connect() as conn:
        user = row(conn, '''SELECT a.id,a.username,a.name,a.role,a.is_active,a.version
            FROM staff_accounts a JOIN staff_sessions s ON s.staff_id=a.id
            WHERE s.token_hash=:token AND s.expires_at>now() AND a.is_active''', token=token_hash(token))
    if user is None:
        raise HTTPException(401, 'Oturum sona erdi. Tekrar giriş yapın.')
    expected_actor = request.headers.get('X-CafeERP-Actor')
    if expected_actor is not None and expected_actor != str(user['id']):
        raise HTTPException(401, 'Tarayıcıdaki personel değişmiş. Tekrar giriş yapın.')
    return user


User = Annotated[dict, Depends(current_user)]


def require_roles(*roles):
    def authorize(user: User):
        if user['role'] not in roles:
            raise HTTPException(403, 'Bu işlem için yetkiniz yok.')
        return user
    return authorize


def audit(conn, actor_id, action, resource, key=None):
    conn.execute(text('''INSERT INTO staff_audit(actor_id,action,resource,request_key)
        VALUES (:actor,:action,:resource,:key)'''),
        {'actor': actor_id, 'action': action, 'resource': str(resource), 'key': key})


def create_first_admin(engine, username, name, password):
    """Yalnızca hesap bulunmayan kurulumda yerel terminalden ilk yönetici açılır."""
    from app.api.auth_routes import NewAccount
    body = NewAccount(username=username, name=name, password=password, role='admin')
    encoded = hash_password(body.password.get_secret_value())
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(68421930)"))
        if conn.execute(text('SELECT 1 FROM staff_accounts LIMIT 1')).first():
            raise ValueError('Personel hesabı mevcut; ilk yönetici kurulumu tekrar çalıştırılamaz.')
        account = row(conn, f'''INSERT INTO staff_accounts(username,name,role,password_hash)
            VALUES (:username,:name,'admin',:password) RETURNING {PUBLIC_FIELDS}''',
            username=body.username, name=body.name, password=encoded)
        audit(conn, account['id'], 'bootstrap', account['id'])
        return account
