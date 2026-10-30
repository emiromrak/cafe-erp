"""Şema geçişlerini yapılandırılmış PostgreSQL veritabanına uygular."""
from alembic import context
from app.database import get_engine

def run_migrations_online():
    # Testler gerçek Alembic zincirini geçici şemadaki bağlantıyla çalıştırır.
    supplied = context.config.attributes.get('connection')
    if supplied is not None:
        context.configure(connection=supplied, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = get_engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=None)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()

run_migrations_online()
