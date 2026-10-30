# 🤖 AGENTS.md - CafeERP Yapay Zeka Ajan Kılavuzu

> Bu dosya, projede çalışan otonom yapay zeka ajanları (Codex, Cursor, Windsurf, AutoGen, CrewAI vb.) için hızlı başlangıç ve çalışma yönergelerini içerir. Ayrıntılı mimari, veritabanı şeması ve matematiksel modeller için lütfen [CODEX.md](CODEX.md) dosyasına başvurun.

---

## 🎯 Ajan Görevi ve Hedefi
CafeERP, modern 3. nesil kahve dükkanları ile geleneksel Türk kafe dinamiklerini birleştiren, yapay zeka destekli bir kafe işletim sistemidir (POS + KDS + Stok + Tahmin).

Bu depoda çalışırken ajanın temel görevi:
1. Mevcut FastAPI backend'i ve yapay zeka karar motorunu korumak ve genişletmek.
2. `docs/ROADMAP.md` sırasına göre önce adisyon ve ödeme backend'ini, ardından uçtan uca POS, stok motoru ve mobil/KDS arayüzlerini mimariye uygun şekilde geliştirmek.
3. Deterministik finansal ve stok hesaplama kurallarını (halüsinasyonsuz mimariyi) asla bozmamak.

---

## 🧭 Hızlı Dizin ve Bileşen Haritası
- `backend/app/main.py`: FastAPI giriş noktası (`uvicorn app.main:app`).
- `backend/app/api/ai_routes.py`: AI REST servisleri (`/api/ai/...`).
- `backend/app/stock_service.py`: kesin hassasiyetli stok, reçete ve üretim tüketimi.
- `backend/app/api/stock_routes.py`: stok hareketleri ve reçete API'leri.
- `docs/STOCK.md`: hazırlıkta tüketim, iptal/zayiat politikası ve kurulum.
- `backend/app/ai/decision_engine.py`: NLU kural motoru ve ciro/yoğunluk/stok sorgulayıcı.
- `backend/app/ai/predictor.py`: LightGBM çıkarımı ve reçete burn-rate simülasyonu.
- `backend/app/ai/weather_service.py`: Open-Meteo canlı hava durumu entegrasyonu.
- `backend/app/ai/telegram_bot.py`: Telegram "Cepteki Müdür" asistanı.
- PostgreSQL: Docker Compose `db` servisi; eski `data/sample_cafe.db` yalnızca aktarım kaynağıdır.
- `migrations/`: Alembic şema geçişleri; `scripts/import_sqlite.py`: tek seferlik örnek veri aktarımı.
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
6. **Commit biçimi ve dili:** Kullanıcı aksini belirtmedikçe `tür(kapsam): Türkçe açıklama` biçimini kullanın (ör. `feat(telegram): mesajların loglanması eklendi`).
7. **Commit ve push düzeni:** Birbirinden bağımsız işleri tek committe toplamayın; değişiklikleri anlamlı ve kendi içinde tutarlı parçalara ayırın, bağımlı commitleri doğru sırayla oluşturun. `git add .` veya `git add -A` kullanmak yerine ilgili dosyaları ya da değişiklik bloklarını açıkça stage edin. Her commitin kapsamını ve gerekli kontrolleri doğrulayın. Kullanıcı push istediğinde bu commitleri mevcut uzak dala normal push ile gönderin; tamamlandıktan sonra yerel/uzak dal eşitliğini ve çalışma ağacını kontrol edin.
