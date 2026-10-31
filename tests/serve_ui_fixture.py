"""Tarayıcı doğrulaması için geçici PostgreSQL şemasıyla izole API sunar.

    docker compose run --rm --no-deps -p 127.0.0.1:8001:8000 api python -B tests/serve_ui_fixture.py

    Durdurulduğunda geçici şema ve tüm test kayıtları kaldırılır.
"""
import uvicorn
from test_tabs import TabTests
from app.main import app
from app import auth
from sqlalchemy import text

if __name__ == '__main__':
    fixture = TabTests('test_migration_preserves_legacy_data_and_is_repeatable')
    try:
        fixture.setUp()
        # Bu parola yalnızca geçici test şemasına aittir; işletme hesabı açılmaz.
        with fixture.engine.begin() as conn:
            conn.execute(text("UPDATE staff_accounts SET password_hash=:hash WHERE username='testadmin'"),
                         {'hash':auth.hash_password('Test-parolasi-2026!')})
        uvicorn.run(app, host='0.0.0.0', port=8000)
    finally:
        fixture.doCleanups()
