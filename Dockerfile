FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend \
    MPLBACKEND=Agg

WORKDIR /app

# LightGBM için gerekli OpenMP çalışma zamanı.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

# Tarih ve saat hesapları kafenin yerel saat dilimini kullanır.
ENV TZ=Europe/Istanbul
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

# Gizli ayarlar ve yerel ortamlar imaja kopyalanmaz.
COPY backend ./backend
COPY data ./data
COPY tests ./tests
COPY requirements.txt ./

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
