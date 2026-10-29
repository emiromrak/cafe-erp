"""PostgreSQL bağlantı ayarları; parolalar yalnızca ortamdan okunur."""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

def get_engine():
    """SQLAlchemy motoru oluşturur; bağlantı ilk sorguya kadar açılmaz."""
    password = os.getenv('POSTGRES_PASSWORD')
    if not password:
        raise RuntimeError('POSTGRES_PASSWORD ortam değişkeni tanımlanmalı.')
    return create_engine(URL.create(
        'postgresql+psycopg', username=os.getenv('POSTGRES_USER', 'cafe_erp'),
        password=password, host=os.getenv('POSTGRES_HOST', '127.0.0.1'),
        port=int(os.getenv('POSTGRES_PORT', '5433')),
        database=os.getenv('POSTGRES_DB', 'cafe_erp'),
    ), pool_pre_ping=True)
