"""Tarayıcı doğrulaması için geçici PostgreSQL şemasıyla izole API sunar.

    docker compose run --rm --no-deps -p 127.0.0.1:8001:8000 api python -B tests/serve_ui_fixture.py

    Durdurulduğunda geçici şema ve tüm test kayıtları kaldırılır.
"""
import uvicorn
from test_tabs import TabTests
from app.main import app

if __name__ == '__main__':
    fixture = TabTests('test_migration_preserves_legacy_data_and_is_repeatable')
    try:
        fixture.setUp()
        uvicorn.run(app, host='0.0.0.0', port=8000)
    finally:
        fixture.doCleanups()
