# 🤖 AGENTS.md - CafeERP Yapay Zeka Ajan Kılavuzu

> Bu dosya, projede çalışan otonom yapay zeka ajanları (Codex, Cursor, Windsurf, AutoGen, CrewAI vb.) için hızlı başlangıç ve çalışma yönergelerini içerir. Ayrıntılı mimari, veritabanı şeması ve matematiksel modeller için lütfen [CODEX.md](CODEX.md) dosyasına başvurun.

---

## 🎯 Ajan Görevi ve Hedefi
CafeERP, modern 3. nesil kahve dükkanları ile geleneksel Türk kafe dinamiklerini birleştiren, yapay zeka destekli bir kafe işletim sistemidir (POS + KDS + Stok + Tahmin).

Bu depoda çalışırken ajanın temel görevi:
1. Mevcut FastAPI backend'i ve yapay zeka karar motorunu korumak ve genişletmek.
2. Faz 2 (Frontend MVP: Next.js PWA, POS, KDS ve Garson arayüzü) geliştirmesini mimariye uygun şekilde gerçekleştirmek.
3. Deterministik finansal ve stok hesaplama kurallarını (halüsinasyonsuz mimariyi) asla bozmamak.

---

## 🧭 Hızlı Dizin ve Bileşen Haritası
- `backend/app/main.py`: FastAPI giriş noktası (`uvicorn app.main:app`).
- `backend/app/api/ai_routes.py`: AI REST servisleri (`/api/ai/...`).
- `backend/app/ai/decision_engine.py`: NLU kural motoru ve ciro/yoğunluk/stok sorgulayıcı.
- `backend/app/ai/predictor.py`: LightGBM çıkarımı ve reçete burn-rate simülasyonu.
- `backend/app/ai/weather_service.py`: Open-Meteo canlı hava durumu entegrasyonu.
- `backend/app/ai/telegram_bot.py`: Telegram "Cepteki Müdür" asistanı.
- `data/sample_cafe.db`: 7 tablodan oluşan SQLite veritabanı (37.000+ gerçekçi sipariş).
- `data/generator/generate_sample_data.py`: Sentetik veri üreteci.

---

## ⚡ Temel Çalıştırma Komutları
- **Backend Sunucusu:** `python backend\app\main.py` (Port: 8000)
- **Telegram Asistanı:** `python backend\app\ai\telegram_bot.py`
- **Model Yeniden Eğitimi:** `python backend\app\ai\train_forecast.py`
- **Örnek Veri Üretimi:** `python data\generator\generate_sample_data.py`
- **Gereksinimler:** `pip install -r requirements.txt`

---

## ⚠️ Ajanlar İçin Katı Kurallar (Strict Constraints)
1. **Yol Belirtimi:** Asla hardcoded mutlak dosya yolu (`C:\...`) yazmayın; daima `Path(__file__).resolve().parent...` kullanın.
2. **Finansal / Stok Hesaplamaları:** Asla LLM'lere matematik veya stok hesabı yaptırmayın. Hesaplamalar %100 Python ve SQL ile deterministik kalmalıdır.
3. **SQLite Kilitlenmesi:** Veritabanı sorgularından sonra bağlantının kapatıldığından (`conn.close()`) emin olun.
4. **Kod Dili ve Yorumlar:** Mevcut Türkçe değişken açıklamalarını ve docstring'leri koruyun.
5. **Gizlilik:** `.env` dosyasındaki token ve hassas bilgileri commit veya print etmeyin.
