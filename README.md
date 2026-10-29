# ☕ CafeERP: Yapay Zeka Destekli Yeni Nesil Kafe İşletim ve Karar Destek Sistemi

> **CafeERP**, modern 3. nesil specialty kahve dükkanları ile geleneksel Türk kafe/kıraathane dinamiklerini birleştiren, makine öğrenmesi destekli akıllı bir kafe yönetim ve karar destek platformudur.

---

## 🌟 Öne Çıkan Özellikler

- **🧠 Makine Öğrenmesi ile Talep & Ciro Tahmini:** LightGBM regresyon modeli, geçmiş 6 aylık saatlik veriyi ve canlı hava durumu koşullarını harmanlayarak günün pik saatlerini ve beklenen satış hacmini öngörür.
- **🥛 Stok & Erime Hızı (Burn-Rate) Simülasyonu:** Yoğunluk tahminine göre çay, süt, ekmek ve kaşarın tükenme saatini hesaplar. Gerçek siparişten reçeteye bağlı otomatik stok düşümü Faz 3 kapsamındadır.
- **🌤️ Canlı Hava Durumu Entegrasyonu:** Open-Meteo REST API ile sıfır konfigürasyon ve ücretsiz olarak kafe bölgesinin sıcaklık ve yağış durumunu çeker.
- **📱 Cepteki Müdür (Telegram Bot Asistanı):** Kafe sahibine sabah brifingi sunar, klavye butonları ve serbest Türkçe NLU motoru ile anlık ciro, yoğunluk ve stok sorgulama imkanı sağlar.
- **⚡ Halüsinasyonsuz Karar Motoru (LLM-less NLU):** Finansal ciro ve stok hesaplamalarında harici LLM maliyeti ve halüsinasyon riski olmadan %100 matematiksel doğrulukla çalışan Türkçe kural motoru.
- **🍽️ Dokunmatik POS & Mobil Garson Terminali (Faz 2):** Tablet üzerinden hızlı kasa satışı, masa krokisi, mutfak ekranı (KDS) ve garsonun masada cep telefonundan sipariş alabilmesi.

---

## 🏗️ Mimari ve Teknoloji Yığını

```mermaid
flowchart TD
    subgraph Istemciler ["İstemciler (Faz 2)"]
        POS["📱 Kasa POS Terminali"]
        Garson["📲 Mobil Garson PWA"]
        KDS["🍳 Mutfak/Barista KDS"]
        Telegram["💬 Telegram Botu (Cepteki Müdür)"]
    end

    subgraph Backend ["Backend Servisi (FastAPI)"]
        API["FastAPI REST Endpoints (/api/ai/...)"]
        Engine["Deterministik Karar Motoru (NLU)"]
        Predictor["LightGBM Tahmin & Burn-Rate Motoru"]
        Weather["Open-Meteo Hava Durumu Servisi"]
    end

    subgraph Veri ["Veri Katmanı"]
        DB[(SQLite / PostgreSQL)]
        Models[("demand_forecast.pkl")]
    end

    Istemciler <--> API
    Telegram <--> Engine
    API <--> Engine
    Engine <--> Predictor
    Engine <--> DB
    Predictor <--> Models
    Weather --> Predictor
```

- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic v2
- **Yapay Zeka & Veri Bilimi:** LightGBM, Pandas, Scikit-learn, Joblib
- **Veritabanı:** SQLite (`data/sample_cafe.db` - 37.000+ gerçekçi sipariş)
- **Frontend (Yol Haritası):** Next.js 14/15, Tailwind CSS, shadcn/ui
- **Harici API'ler:** Open-Meteo API, Telegram Bot API

---

## 📁 Proje Dizin Yapısı

Detaylı dosya ve kod haritası için **[CODEX.md](CODEX.md)** belgesine bakınız.

```
cafe_erp/
├── CODEX.md                     # Yapay zeka ajanları ve Codex için ana referans
├── AGENTS.md                    # Multi-agent sistemler için rehber
├── requirements.txt             # Proje Python bağımlılıkları
├── backend/
│   └── app/
│       ├── main.py              # FastAPI sunucu giriş noktası
│       ├── api/ai_routes.py     # AI REST rotaları
│       └── ai/                  # Tahmin modeli, karar motoru ve Telegram botu
├── data/
│   ├── sample_cafe.db           # SQLite veritabanı (Menü, Reçeteler, Masalar, Siparişler)
│   └── generator/               # Gerçekçi sentetik veri üreteci
├── tests/                       # Çekirdek ve API entegrasyon testleri
├── scripts/reports/             # Rapor, grafik ve şablon inceleme araçları
└── docs/                        # Mimari, geliştirme notları ve görseller
```

---

## 🚀 Hızlı Başlangıç (Quickstart)

Uygulama kodu `backend/`, örnek veriler `data/`, testler `tests/` altındadır.
Rapor araçlarının kullanımı için [scripts/reports/README.md](scripts/reports/README.md)
dosyasına bakınız. Yerel Word şablonları `docs/templates/`, üretilen raporlar
`docs/output/` altında tutulur.

### 1. Kurulum
```bash
git clone <repo-url>
cd cafe_erp
pip install -r requirements.txt
```

### 2. Ortam Değişkenleri (`.env`)
Kök dizinde `.env` dosyasını oluşturun:
```env
TELEGRAM_BOT_TOKEN="your_bot_token_here"
TELEGRAM_ALLOWED_USER_IDS="123456789"
CAFE_LATITUDE=37.7647
CAFE_LONGITUDE=30.5567
```

`.env.example` dosyası örnek ayarları içerir. `TELEGRAM_ALLOWED_USER_IDS`, virgülle ayrılmış Telegram kullanıcı kimlikleridir. Bot yalnızca bu kullanıcıların özel sohbetlerine yanıt verir; liste boşsa başlamaz. Konum belirtilmezse Kadıköy koordinatları kullanılır.

### 3. FastAPI Backend Servisini Başlatma
```bash
python backend/app/main.py
```
Sunucu `http://127.0.0.1:8000` adresinde ayağa kalkacaktır. Etkileşimli Swagger API dokümantasyonu: `http://127.0.0.1:8000/docs`

### 4. Telegram Botunu Başlatma
```bash
python backend/app/ai/telegram_bot.py
```

### 5. Modelleri ve Veriyi Yeniden Üretme (Opsiyonel)
```bash
# Örnek veritabanını oluşturma
python data/generator/generate_sample_data.py

# LightGBM tahmin modelini eğitme
python backend/app/ai/train_forecast.py
```

---

## 🗺️ Geliştirme Yol Haritası (Roadmap)

- [x] **Faz 1: Çekirdek Veritabanı & Simülatör:** Menü, reçeteler, masalar ve 37.000+ geçmiş sipariş verisi.
- [x] **Faz 4: Yapay Zeka & Tahmin Katmanı:** LightGBM talep modeli, reçete burn-rate, hava durumu servisi, NLU karar motoru, Telegram botu.
- [ ] **Faz 2: Kullanıcı Arayüzü & Frontend MVP (Sıradaki Adım):** Next.js PWA ile dokunmatik tablet POS ekranı, masa krokisi, mobil garson el terminali ve KDS mutfak ekranı.
- [ ] **Faz 3: Reçete ve Stok Düşüm Olay Motoru:** Sipariş kapandığında hammadde stoklarını anlık eksilten servis.
- [ ] **Faz 5: Pilot Kafe Saha Denemesi:** Gerçek işletmede canlı test.

---

## 📄 Detaylı Dokümantasyon

Çekirdek doğruluk düzeltmeleri, test komutu ve güncel sınırlamalar için [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) dosyasına bakınız.

- **[CODEX.md](CODEX.md):** Codex ve otonom kodlama ajanları için eksiksiz bilgi bankası.
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md):** Sistem mimarisi ve PostgreSQL şeması.
- **[docs/MODULES_AND_FLOWS.md](docs/MODULES_AND_FLOWS.md):** Operasyonel akışlar (POS, KDS, Garson).
- **[docs/FISCAL_AND_MVP_STRATEGY.md](docs/FISCAL_AND_MVP_STRATEGY.md):** Türkiye ÖKC ve mali mevzuat yaklaşımı.
- **[docs/ROADMAP.md](docs/ROADMAP.md):** Faz bazlı geliştirme planı.
