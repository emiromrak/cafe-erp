"""Personel girişi, çıkışı ve yöneticiye özel hesap yönetimi."""
import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, SecretStr, StringConstraints
from sqlalchemy import text

from app import auth
from app.ai import decision_engine
from app.transactions import row

router = APIRouter(prefix='/api/auth', tags=['Personel ve erişim'])
Username = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, pattern=r'^[a-z0-9_.-]{3,50}$')]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Role = Literal['admin', 'cashier', 'waiter', 'kitchen']
Admin = Annotated[dict, Depends(auth.require_roles('admin'))]


def numeric_password(value: SecretStr):
    auth.validate_password(value.get_secret_value())
    return value


NumericPassword = Annotated[SecretStr, Field(min_length=4, max_length=128), AfterValidator(numeric_password)]


class Login(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    username: Username
    password: Annotated[SecretStr, Field(min_length=1, max_length=128)]


class NewAccount(Login):
    name: Name
    role: Role
    password: NumericPassword


class ChangeAccount(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    name: Name
    role: Role
    is_active: bool
    expected_version: Annotated[int, Field(strict=True, ge=0, le=9223372036854775806)]
    password: NumericPassword | None = None


# Var olmayan kullanıcıda da aynı maliyetle parola doğrulanır.
_DUMMY = auth.hash_password(''.join(secrets.choice('0123456789') for _ in range(32)))


@router.post('/login')
def login(body: Login, response: Response, request: Request):
    token = secrets.token_urlsafe(32)
    with decision_engine._engine().begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(68421931)'))
        conn.execute(text("DELETE FROM login_attempts WHERE attempted_at < now()-interval '15 minutes'"))
        conn.execute(text('DELETE FROM staff_sessions WHERE expires_at<=now()'))
        attempts = conn.execute(text('''SELECT count(*) FROM login_attempts
            WHERE attempted_at>now()-interval '1 minute' ''')).scalar_one()
        failures = conn.execute(text('SELECT count(*) FROM login_attempts WHERE username=:name AND NOT success'),
                                {'name': body.username}).scalar_one()
        if failures >= 5 or attempts >= 60:
            raise HTTPException(429, 'Çok fazla giriş denemesi. Daha sonra tekrar deneyin.', headers={'Retry-After':'900'})
        account = row(conn, 'SELECT * FROM staff_accounts WHERE username=:name FOR SHARE', name=body.username)
        valid = auth.verify_password(body.password.get_secret_value(), account['password_hash'] if account else _DUMMY)
        valid = bool(valid and account and account['is_active'])
        conn.execute(text('INSERT INTO login_attempts(username,success) VALUES (:name,:success)'),
                     {'name': body.username, 'success': valid})
        if valid:
            conn.execute(text('''INSERT INTO staff_sessions(token_hash,staff_id,expires_at)
                VALUES (:token,:id,now()+interval '12 hours')'''),
                {'token': auth.token_hash(token), 'id': account['id']})
            # Aynı tarayıcının önceki oturumu giriş sırasında yenilenir.
            previous = request.cookies.get(auth.COOKIE)
            if previous:
                conn.execute(text('DELETE FROM staff_sessions WHERE token_hash=:hash'), {'hash':auth.token_hash(previous)})
            auth.audit(conn, account['id'], 'login', account['id'])
    # Başarısız deneme kaydı HTTP hatasıyla geri alınmamalı.
    if not valid:
        raise HTTPException(401, 'Kullanıcı adı veya parola hatalı.')
    response.set_cookie(auth.COOKIE, token, max_age=auth.SESSION_SECONDS,
                        httponly=True, secure=auth.secure_cookie(), samesite='strict', path='/')
    return {field: account[field] for field in auth.PUBLIC_FIELDS.split(',')}


@router.get('/me')
def me(user: auth.User):
    return user


@router.get('/switchable-staff')
def switchable_staff(user: auth.User):
    """Ortak POS'ta hesap seçimi; yalnızca aktif personelin temel bilgileri."""
    with decision_engine._engine().connect() as conn:
        return [dict(r) for r in conn.execute(text('''SELECT id,username,name,role
            FROM staff_accounts WHERE is_active ORDER BY name,id''')).mappings()]


@router.post('/logout')
def logout(request: Request, response: Response):
    with decision_engine._engine().begin() as conn:
        conn.execute(text('DELETE FROM staff_sessions WHERE token_hash=:token'),
                     {'token': auth.token_hash(request.cookies.get(auth.COOKIE, ''))})
    response.delete_cookie(auth.COOKIE, path='/', httponly=True,
                           secure=auth.secure_cookie(), samesite='strict')
    return {'logged_out': True}


@router.get('/staff')
def staff(user: Admin):
    with decision_engine._engine().connect() as conn:
        return [dict(r) for r in conn.execute(text(f'SELECT {auth.PUBLIC_FIELDS} FROM staff_accounts ORDER BY id')).mappings()]


def lock_admin(conn, user):
    """Hesap yönetimini sıralar; son aktif yöneticinin kaybolmasını önler."""
    conn.execute(text('SELECT pg_advisory_xact_lock(68421930)'))
    current = row(conn, 'SELECT * FROM staff_accounts WHERE id=:id FOR UPDATE', id=user['id'])
    if not current or not current['is_active'] or current['role'] != 'admin' or current['version'] != user['version']:
        raise HTTPException(401, 'Yönetici oturumu değişmiş. Tekrar giriş yapın.')


@router.post('/staff', status_code=201)
def create_staff(body: NewAccount, user: Admin):
    encoded = auth.hash_password(body.password.get_secret_value())
    with decision_engine._engine().begin() as conn:
        lock_admin(conn, user)
        if row(conn, 'SELECT id FROM staff_accounts WHERE username=:name', name=body.username):
            raise HTTPException(409, 'Bu kullanıcı adı mevcut.')
        created = row(conn, f'''INSERT INTO staff_accounts(username,name,role,password_hash)
            VALUES (:username,:name,:role,:password) RETURNING {auth.PUBLIC_FIELDS}''',
            username=body.username, name=body.name, role=body.role, password=encoded)
        auth.audit(conn, user['id'], 'staff_created', created['id'])
        return created


@router.patch('/staff/{staff_id}')
def change_staff(staff_id: Annotated[int, Field(gt=0, le=9223372036854775807)], body: ChangeAccount, user: Admin):
    encoded = auth.hash_password(body.password.get_secret_value()) if body.password is not None else None
    with decision_engine._engine().begin() as conn:
        lock_admin(conn, user)
        target = row(conn, 'SELECT * FROM staff_accounts WHERE id=:id FOR UPDATE', id=staff_id)
        if not target:
            raise HTTPException(404, 'Personel bulunamadı.')
        if target['version'] != body.expected_version:
            raise HTTPException(409, 'Personel kaydı değişmiş. Listeyi yenileyin.')
        if target['role'] == 'admin' and target['is_active'] and (body.role != 'admin' or not body.is_active):
            count = conn.execute(text("SELECT count(*) FROM staff_accounts WHERE role='admin' AND is_active")).scalar_one()
            if count <= 1:
                raise HTTPException(409, 'Son aktif yönetici devre dışı bırakılamaz veya rolü değiştirilemez.')
        changed = row(conn, f'''UPDATE staff_accounts SET name=:name,role=:role,is_active=:active,
            password_hash=coalesce(:password,password_hash),version=version+1
            WHERE id=:id RETURNING {auth.PUBLIC_FIELDS}''', id=staff_id, name=body.name,
            role=body.role, active=body.is_active, password=encoded)
        conn.execute(text('DELETE FROM staff_sessions WHERE staff_id=:id'), {'id': staff_id})
        auth.audit(conn, user['id'], 'staff_changed', staff_id)
        return changed
