"""Şema geçişlerini yapılandırılmış PostgreSQL veritabanına uygular."""
from alembic import context
from app.database import get_engine

def run_migrations_online():
    engine = get_engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=None)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()

run_migrations_online()
