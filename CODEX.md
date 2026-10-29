# 📖 CODEX.md - CafeERP Proje Bilgi Bankası ve Yapay Zeka Ajan Rehberi

> **Bu dosya, projede çalışan OpenAI Codex, Cursor, GitHub Copilot, Claude Code ve diğer tüm yapay zeka kodlama ajanları için tek ve yetkili rehberdir.** Projenin mimarisi, iş kuralları, veritabanı şeması, yapay zeka tahmin motoru, operasyonel akışları ve geliştirme standartları eksiksiz olarak burada belgelenmiştir.

---

## 1. Projeye Genel Bakış (Executive Overview)

- **Proje Adı:** CafeERP (Yapay Zeka Destekli Yeni Nesil Kafe İşletim ve Karar Destek Sistemi)
- **Vizyon:** Türkiye'deki kafe kültürünün gerçeklerine uygun; hem modern 3. nesil specialty kahve dükkanlarının (Latte, V60, bitkisel sütler, karton bardak sarfiyatı) hem de geleneksel Türk kafe/kıraathane dinamiklerinin (bardak çay, demlik semaver, kaşarlı tost, okey/tavla masaları, yoğun akşam çay tüketimi) ihtiyaçlarını birleştiren, **makine öğrenmesi destekli** uçtan uca operasyonel ERP.
- **Temel Problem:**
  1. Yüksek hammadde firesi ve kontrolsüz stok erimesi (özellikle süt, ekmek, çay yaprağı).
  2. Yoğun saatlerin (pik) kestirilememesi sebebiyle yanlış vardiya/personel planlaması.
  3. Kafe sahibinin anlık ciro, masa devir hızı ve tükenme alarmlarını tek ekranda görememesi.
  4. Mevcut piyasa yazılımlarının yüksek maliyeti, hantal arayüzleri ve proaktif karar destek sunmaması.
- **Çözüm:**
  - Restoran/Kafe POS, Mutfak Ekranı (KDS) ve Mobil Garson El Terminali (PWA).
  - Canlı hava durumu ve LightGBM ile saatlik talep ve ciro tahmini.
  - Reçete (BOM) bazlı dinamik stok düşümü ve erime hızı (burn-rate) alarmları.
  - Harici LLM maliyeti ve halüsinasyon riski olmayan %100 deterministik Türkçe Karar Motoru (NLU).
  - Kafe sahibinin cebindeki müdür: Telegram Asistan Botu.

---

## 2. Dizin Yapısı ve Dosya Haritası (Repository Structure)

```
cafe_erp/
│
├── CODEX.md                     # [BU DOSYA] Codex & AI ajanları için ana başvuru rehberi
├── AGENTS.md                    # Çoklu ajan sistemleri (Multi-agent harness) için kılavuz
├── README.md                    # İnsan ve geliştirici odaklı genel proje tanıtımı
├── .cursorrules                 # Cursor ve IDE yapay zeka kuralları
├── requirements.txt             # Python bağımlılıkları (FastAPI, LightGBM, Pandas vb.)
├── .env                         # Telegram bot token, GPS koordinatları (Gizli değişkenler)
├── .gitignore                   # Git yoksayma kuralları
├── telegram_messages.log        # Telegram botu üzerinden gelen mesajların canlı kayıt kütüğü
│
├── backend/                     # FastAPI Backend Servisi
│   ├── requirements.txt         # Backend'e özel Python paketleri
│   └── app/
│       ├── main.py              # FastAPI giriş noktası, CORS ve router yapılandırması
│       ├── api/
│       │   └── ai_routes.py     # /api/ai/... REST endpoint'leri (Satış, Yoğunluk, Stok, Brifing)
│       └── ai/                  # Yapay Zeka & Karar Motoru Katmanı
│           ├── decision_engine.py  # Deterministik NLU kural motoru ve SQLite sorgulayıcı
│           ├── predictor.py        # LightGBM çıkarım (inference) ve saatlik reçete burn-rate simülasyonu
│           ├── train_forecast.py   # LightGBM regresyon modellerini eğiten eğitim betiği
│           ├── weather_service.py  # Open-Meteo REST API canlı hava durumu entegrasyonu
│           ├── telegram_bot.py     # Telegram Botu ("Cepteki Müdür" - polling ve mesaj yönetimi)
│           └── models/
│               └── demand_forecast.pkl  # Eğitilmiş LightGBM modelleri ve özellik sütunları
│
├── data/                        # Veritabanı ve Veri Üreteçleri
│   ├── sample_cafe.db           # SQLite veritabanı (Menü, Reçeteler, Stoklar, 37.000+ Sipariş)
│   ├── sample_cafe_data.json    # JSON formatında dışa aktarılmış tam veri seti
│   └── generator/
│       └── generate_sample_data.py # 6 aylık sentetik gerçekçi kafe verisi üreten betik
│
├── docs/                        # Mimari ve Dokümantasyon Belgeleri
│   ├── ARCHITECTURE.md          # Sistem mimarisi, PostgreSQL/Redis hedef mimarisi
│   ├── MODULES_AND_FLOWS.md     # POS, KDS, Garson Terminali ve AI temas noktaları
│   ├── ROADMAP.md               # 5 fazlı geliştirme yol haritası
│   ├── FISCAL_AND_MVP_STRATEGY.md # Türkiye yasal ÖKC / Mali fiş stratejisi ve MVP ayrımı
│   └── images/                  # Arayüz taslakları, Gantt şeması ve mimari diyagramlar
│
└── [Rapor ve Görselleştirme Betikleri]
    ├── build_clean_doc.py       # Tasarım 1 Akademik/Mühendislik Raporu Word derleyicisi
    ├── generate_chart.py        # Çalışma takvimi Gantt şeması üreteci (Matplotlib)
    ├── generate_flowchart.py    # Sistem yöntem akış şeması üreteci (Matplotlib)
    └── inspect_*.py             # Rapor şablonu inceleme ve düzeltme yardımcıları
```

---

## 3. Sistem Mimarisi ve Teknoloji Yığını (Tech Stack)

### A. Teknoloji Bileşenleri
| Katman | Teknoloji / Kütüphane | Rolü ve Açıklaması |
| :--- | :--- | :--- |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2 | Yüksek performanslı asenkron REST API servisi |
| **Veri Katmanı (MVP)** | SQLite (`data/sample_cafe.db`) | Geliştirme, prototipleme ve hafif çalışma ortamı |
| **Veri Katmanı (Prod Hedefi)** | PostgreSQL + `pgvector` + Redis | Çok şubeli yapı, adisyon önbelleği ve semantik menü arama |
| **Makine Öğrenmesi (ML)** | LightGBM, Scikit-learn, Pandas | Hava durumu ve zamana bağlı saatlik talep/ciro tahmini |
| **Karar Motoru (NLU)** | Kural Tabanlı Uzman Sistem (`decision_engine.py`) | Harici LLM olmadan %100 deterministik, sıfır halüsinasyonlu Türkçe yanıtlar |
| **Dış Servisler** | Open-Meteo REST API | API anahtarsız, ücretsiz canlı sıcaklık ve hava kodu servisi |
| **Mobil/Müdür Arayüzü** | Telegram Bot API | Kafe sahibine anlık bildirim, klavye butonları ve serbest soru yanıtlama |
| **Frontend (Faz 2 Hedefi)** | Next.js 14/15, Tailwind CSS, shadcn/ui | Dokunmatik POS, KDS Mutfak Ekranı ve Garson PWA |

### B. Mimari Veri Akış Şeması
```
[ Open-Meteo API ] --------> weather_service.py
                                   │
                                   ▼
[ SQLite (sample_cafe.db) ] ──> decision_engine.py <── predictor.py <── demand_forecast.pkl
                                   │
             ┌─────────────────────┴─────────────────────┐
             ▼                                           ▼
      FastAPI Endpoints                           telegram_bot.py
      (/api/ai/...)                               (Cepteki Müdür)
             │                                           │
             ▼                                           ▼
   Web POS / KDS / Garson PWA                     Kafe Sahibi (Telegram)
```

---

## 4. Veritabanı Şeması ve Veri Modelleri (SQLite: `data/sample_cafe.db`)

Veritabanında 7 adet çekirdek tablo bulunur:

### 1. `raw_materials` (Depo ve Hammadde Stokları)
- `id` (TEXT, PK): Hammadde benzersiz kodu (örn: `rm_tea_leaf`, `rm_milk_whole`, `rm_coffee_blend`, `rm_cheese_kasar`, `rm_bread_toast`).
- `name` (TEXT): Hammadde adı (örn: *"Rize Çay Yaprağı (Dökme)"*, *"Tam Yağlı Süt"*).
- `category` (TEXT): Kategori (`Çay`, `Kahve`, `Süt`, `Mutfak`, `İçecek`, `Tatlı`, `Pastane`, `Sarf`, `Ambalaj`).
- `unit` (TEXT): Ölçü birimi (`gram`, `ml`, `dilim`, `adet`).
- `current_stock` (REAL): Depodaki güncel miktar.
- `min_alert` (REAL): Kritik stok uyarı eşiği.
- `cost` (REAL): Birim maliyet (TL).

### 2. `products` (Menü Ürünleri)
- `id` (TEXT, PK): Ürün kodu (örn: `prod_tea_glass`, `prod_latte`, `prod_toast_mixed`, `prod_san_sebastian`).
- `cat_id` (TEXT): Kategori referansı (`cat_traditional`, `cat_hot_coffee`, `cat_cold_drinks`, `cat_food_kitchen`, `cat_bakery`).
- `name` (TEXT): Ürün satış adı.
- `price` (REAL): Satış fiyatı (TL).
- `type` (TEXT): Ürün tipi (`tea`, `hot`, `cold`, `food`).

### 3. `dining_tables` (Masalar ve Alanlar)
- `id` (TEXT, PK): Masa kodu (örn: `tbl_salon_1`, `tbl_bahce_2`, `tbl_okey_3`, `tbl_paket`).
- `table_number` (TEXT): Görünen ad (*"Masa 1"*, *"Bahçe 2"*, *"Okey Masası 3"*, *"Paket Servis / Gel-Al"*).
- `capacity` (INTEGER): Kişi kapasitesi (2, 4, 8).
- `area` (TEXT): Bölüm (`Salon`, `Bahçe`, `Okey Alanı`, `Paket`).
- `status` (TEXT): Durum (`empty`, `occupied`, `reserved`).

### 4. `staff` (Personel)
- `id` (TEXT, PK): Personel kodu (`stf_admin_1`, `stf_waiter_1`, `stf_barista_1`).
- `name` (TEXT): Personel adı soyadı.
- `role` (TEXT): Rol (`Yönetici`, `Kasiyer`, `Garson`, `Barista / Çaycı`).
- `pin_code` (TEXT): POS hızlı giriş PIN kodu (4 haneli).
- `is_active` (INTEGER): Aktiflik durumu (1/0).

### 5. `orders` (Adisyonlar ve Sipariş Başlıkları)
- `order_id` (TEXT, PK): Sipariş numarası (örn: `ORD_20260401_0001`).
- `table_id` (TEXT, FK -> dining_tables.id): Masanın kodu.
- `staff_id` (TEXT, FK -> staff.id): Siparişi açan personel.
- `timestamp` (TEXT): Sipariş zamanı (`YYYY-MM-DD HH:MM:SS`).
- `total_amount` (REAL): Toplam hesap tutarı (TL).
- `payment_method` (TEXT): Ödeme tipi (`Nakit`, `Kredi Kartı`).
- `status` (TEXT): Durum (`closed`, `open`, `cancelled`).

### 6. `order_items` (Adisyon Kalemleri)
- `id` (INTEGER, PK Autoincrement): Kalem ID.
- `order_id` (TEXT, FK -> orders.order_id): Ait olduğu sipariş.
- `product_name` (TEXT): Satılan ürünün adı.
- `quantity` (INTEGER): Adet.
- `unit_price` (REAL): Birim satış fiyatı.

### 7. Reçeteler (BOM - Bill of Materials / Ürün Reçeteleri)
Python kodu içerisinde tanımlanmış ve stok erimesinde kullanılan çekirdek reçete formülleri:
- **Bardak Çay (`prod_tea_glass`):** 3.0g çay yaprağı (`rm_tea_leaf`) + 2.0 adet küp şeker (`rm_sugar_cube`).
- **Demlik Çay (`prod_tea_pot`):** 25.0g çay yaprağı + 8.0 adet küp şeker.
- **Caffe Latte (`prod_latte`):** 18.0g kahve çekirdeği + 220ml tam yağlı süt + 1 karton bardak + 1 kapak.
- **Flat White (`prod_flat_white`):** 18.0g kahve çekirdeği + 150ml tam yağlı süt.
- **Americano (`prod_americano`):** 18.0g kahve çekirdeği + 1 bardak + 1 kapak.
- **Kaşarlı Tost (`prod_toast_cheese`):** 2 dilim tost ekmeği + 55g taze kaşar + 10g tereyağı.
- **Karışık Tost (`prod_toast_mixed`):** 2 dilim tost ekmeği + 40g taze kaşar + 35g sucuk + 10g tereyağı.

---

## 5. Yapay Zeka Katmanı ve Tahmin Motoru (AI Engine Deep-Dive)

### A. LightGBM Talep & Satış Tahmini (`train_forecast.py` & `predictor.py`)
- **Eğitim Verisi:** 6 aylık (~37.000+) saatlik olarak toplanmış gerçekçi satış geçmişi.
- **Özellik Vektörü (Feature Columns):**
  - `hour`: Günün saati (8 - 22 arası).
  - `day_of_week`: Haftanın günü (0: Pazartesi ... 6: Pazar).
  - `is_weekend`: Hafta sonu bayrağı (1/0).
  - `is_wednesday`: Çarşamba öğrenci/oyun gecesi bayrağı (1/0).
  - `temperature`: Hava sıcaklığı (°C).
  - `weather_Bulutlu`, `weather_Güneşli`, `weather_Rüzgarlı`, `weather_Yağmurlu`: One-hot hava koşulları.
- **Hedef Değişkenler (Multi-Target Regression):**
  - `traffic`: Beklenen saatlik sipariş/müşteri sayısı.
  - `tea`: Beklenen saatlik bardak çay adedi.
  - `toast`: Beklenen saatlik tost adedi.
  - `hot_coffee`: Beklenen saatlik sıcak kahve adedi.
  - `cold_drink`: Beklenen saatlik soğuk meşrubat adedi.
  - `revenue`: Beklenen saatlik toplam ciro (TL).

### B. Dinamik Reçete Erime Hızı (Burn-Rate) Simülasyonu
`DemandPredictor.simulate_day_burn_rate()` metodu:
1. Günün 08:00 - 22:00 saatleri arasındaki tahmini ürün tüketimlerini hesaplar.
2. Saatlik tahminleri hammadde reçeteleriyle çarpar:
   - Saatlik Çay Tüketimi = `predicted_tea_glasses * 3.0g`
   - Saatlik Süt Tüketimi = `predicted_hot_coffee * 0.70 * 180.0ml`
   - Saatlik Ekmek Tüketimi = `predicted_toasts * 2.0 dilim`
   - Saatlik Kaşar Tüketimi = `predicted_toasts * 55.0g`
3. Depodaki mevcut stoktan saat saat eksiltir.
4. Stok sıfırın altına indiği saati yakalar ve **🚨 Erken Tedarik Alarmı** üretir (Örn: *"Tam Yağlı Süt saat 16:00 civarında tükenebilir! Tedarikçiyi aramalısınız."*).

### C. Hava Durumu Servisi (`weather_service.py`)
- API: [Open-Meteo Forecast API](https://api.open-meteo.com/v1/forecast)
- Parametreler: Latitude ve Longitude (`.env` dosyasından okunur; varsayılan: Isparta / Kadıköy).
- API Key gerektirmez, tamamen ücretsizdir.
- WMO hava kodları `Güneşli`, `Bulutlu`, `Yağmurlu`, `Rüzgarlı` olarak etiketlenir.
- Ağ hatası veya bağlantı kopmasında çökmeyen güvenli yedek (fallback) mekanizmasına sahiptir.

### D. Kural Tabanlı Uzman Karar Motoru (`decision_engine.py`)
- **Neden Harici LLM Yok?** Finansal ciro hesaplarında, adisyon tutarlarında ve stok gramajlarında LLM'lerin halüsinasyon görme riski kabul edilemez. Bu motor, doğrudan SQLite veritabanına SQL sorgusu atarak matematiksel kesinlik sağlar, mikro-saniye hızında çalışır ve API fatura maliyeti çıkarmaz.
- **Niyetler (Intents):**
  1. `SALES_SUMMARY`: Ciro, sipariş sayısı, ortalama sepet, nakit/kart dağılımı, en çok satan 5 ürün.
  2. `TRAFFIC_FORECAST`: Beklenen müşteri hacmi, pik saati, beklenen ürün sayıları.
  3. `STOCK_STATUS`: Kritik eşikteki hammaddeler ve gün içi saatlik tükenme uyarıları.
  4. `SHIFT_ADVICE`: Pik saatine göre (+1 barista) personel tavsiyesi.
  5. `DAILY_BRIEF`: Sabah kafe açılışında sunulan tam operasyonel brifing.
  6. `GREETING`: Hoş geldin mesajı ve hızlı menü yönlendirmesi.

### E. Telegram Akıllı Asistanı ("Cepteki Müdür" - `telegram_bot.py`)
- Telegram Bot API üzerinden `getUpdates` long-polling ile çalışır.
- Kalıcı alt menü klavyesi sunar (`💰 Bugünkü Ciro & Satış`, `👥 Kafe Yoğunluğu & Tahmin`, `🥛 Kritik Stok & Uyarılar`, `📋 Günün Özeti & Brifing`).
- Kafe sahibinin klavye haricinde yazdığı serbest Türkçe cümleleri NLU motorundan geçirerek yanıtlar.
- Gelen tüm mesajları `telegram_messages.log` kütüğüne saat ve kullanıcı ID'siyle kaydeder.

---

## 6. API Endpoint Referansı (FastAPI)

Tüm endpoint'ler `http://127.0.0.1:8000` üzerinde sunulur:

| Metot | URL | Açıklama |
| :--- | :--- | :--- |
| `GET` | `/` | API durumu, sürüm ve dokümantasyon bağlantısı |
| `GET` | `/docs` | Otomatik Swagger UI etkileşimli dokümantasyon |
| `GET` | `/api/ai/sales-summary?date=YYYY-MM-DD` | Günlük satış, ciro, nakit/kart ve çok satanlar (Tarih verilmezse son aktif günü alır) |
| `GET` | `/api/ai/traffic-forecast` | Canlı hava durumu ve saatlik yoğunluk tahmini |
| `GET` | `/api/ai/stock-status` | Kritik stoklar ve saatlik hammadde erime (burn-rate) alarmları |
| `GET` | `/api/ai/daily-brief` | Kafe yöneticisi sabah brifingi özeti |
| `POST` | `/api/ai/query` | Serbest Türkçe soru çözümleyici (Gövde: `{"query": "bugün ciro ne kadar"}`) |

---

## 7. Türkiye Mali Mevzuat & MVP Stratejisi (ÖKC Ayrımı)

Türkiye'de restoran ve kafeler Gelir İdaresi Başkanlığı (GİB) onaylı Ödeme Kaydedici Cihaz (ÖKC - Beko, Ingenico, Hugin vb.) kullanmak zorundadır.

- **MVP Stratejimiz:** Donanım entegrasyonu (yazarkasaya doğrudan kablo/Bluetooth protokolü yazmak), üretici lisanslama ücretleri ve GİB test süreçleri aylar sürdüğü için **MVP kapsamı dışındadır**.
- **Sahadaki Çalışma Şekli:** Türkiye'deki butik kafelerin büyük çoğunluğunun yaptığı gibi:
  - CafeERP; masa takibi, garson siparişleri, reçete stok düşümü ve mutfak KDS ekranını yönetir.
  - Ödeme anında kasiyer, toplam tutarı masadaki mevcut banka/yazarkasa POS cihazına elle tuşlayıp fişi keser ve CafeERP'de "Ödendi" butonuna basar.
  - Bu yöntem yasalara %100 uygundur ve sistemi donanım bağımlılığından kurtarır.
- **Sonraki Faz Hedefi:** E-Arşiv / E-Fatura entegratörleri (Paraşüt, KolayBi) ve popüler ÖKC API protokolleri eklenecektir.

---

## 8. Çalıştırma, Test ve İşletim Komutları (Run Commands)

Tüm komutlar projenin kök dizininde (`c:\Users\Emir\Desktop\projects\cafe_erp`) çalıştırılmalıdır:

### 1. Bağımlılıkları Yükleme
```powershell
pip install -r requirements.txt
```

### 2. FastAPI Backend Sunucusunu Başlatma
```powershell
python backend\app\main.py
# veya Uvicorn ile:
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
API arayüzü: `http://127.0.0.1:8000/docs`

### 3. Telegram Botunu Başlatma
```powershell
python backend\app\ai\telegram_bot.py
```
*(Arka planda çalışır, gelen mesajları konsola ve `telegram_messages.log` dosyasına yazar).*

### 4. Örnek Veritabanını Sıfırdan Yeniden Üretme
```powershell
python data\generator\generate_sample_data.py
```
*(37.000+ sipariş, menü, hammadde ve masaları yeniden oluşturup `sample_cafe.db`ye yazar).*

### 5. Makine Öğrenmesi Modelini Yeniden Eğitme
```powershell
python backend\app\ai\train_forecast.py
```
*(Veritabanındaki siparişleri saatlik olarak gruplar, LightGBM modellerini eğitir ve `backend/app/ai/models/demand_forecast.pkl` dosyasını günceller).*

### 6. Hızlı Karar Motoru Testi (CLI)
```powershell
python -c "from backend.app.ai.decision_engine import decision_engine; print(decision_engine.get_daily_brief()['formatted_text'])"
```

---

## 9. Codex ve AI Ajanları İçin Kodlama Standartları (Rules & Guidelines)

Bu projede kod yazarken veya değişiklik yaparken aşağıdaki kurallara **mutlaka** uyulmalıdır:

1. **Göreceli / Mutlak Yol Güvenliği (Path Resolution):**
   - Dosya yollarını sabit string olarak yazmayın (`"C:/..."` veya `"data/sample.db"`).
   - Daima `Path(__file__).resolve().parent...` yapısını kullanın. Bu sayede kod hem Windows hem Linux sunucularda ve farklı çalışma dizinlerinde hatasız çalışır.
2. **Deterministik İş Mantığı (No LLM for Financial Math):**
   - Kasa cirosu, fiş toplamı, vergi veya hammadde tüketimi gibi operasyonel hesaplamalarda asla olasılıksal (probabilistic) LLM çağrılarına güvenmeyin.
   - Doğrudan `sqlite3` sorguları veya matematiksel Python fonksiyonları kullanılmalıdır.
3. **SQLite Bağlantı Yönetimi:**
   - SQLite bağlantılarını (`conn`) işlem bittikten sonra daima `conn.close()` ile kapatın veya `with` context manager kullanın. Windows ortamında kapatılmayan bağlantılar dosya kilitlenme (`database is locked`) hatalarına yol açar.
4. **Windows Konsol ve Türkçe Karakter Desteği:**
   - Konsola çıktı basan betiklerin başında Türkçe karakter ve emojilerin çökmemesi için mutlaka şu blok bulunmalıdır:
     ```python
     import sys
     if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
         try:
             sys.stdout.reconfigure(encoding='utf-8')
         except Exception:
             pass
     ```
5. **Hassas Bilgiler (Secrets):**
   - API anahtarlarını, Telegram bot tokenlerini asla kaynak kod içine gömmeyin. Daima `.env` ve `python-dotenv` kullanın.
6. **Mevcut Yorum ve Dokümantasyonun Korunması:**
   - Kodları refactor ederken mevcut Türkçe docstring ve açıklama satırlarını silmeyin; geliştirilen yeni fonksiyonlara da aynı detayda docstring ekleyin.

---

## 10. Geliştirme Yol Haritası ve Sıradaki Görevler (Roadmap & Next Steps)

- [x] **Faz 1: Çekirdek Veritabanı & Simülatör (TAMAMLANDI)**
  - SQLite veritabanı, 37.000+ siparişlik örnek veri seti, menü, hammadde ve masa tanımları.
- [x] **Faz 4: Yapay Zeka & Tahmin Katmanı (TAMAMLANDI)**
  - LightGBM regresyon modeli, Open-Meteo hava servisi, deterministik NLU motoru, Telegram asistanı, FastAPI `/api/ai/...` endpoint'leri.
- [ ] **Faz 2: Kullanıcı Arayüzü & Frontend MVP (SIRADAKİ ÖNCELİKLİ GÖREV)**
  - `frontend/` dizini altında Next.js 14/15 PWA oluşturulması.
  - Tailwind CSS + shadcn/ui ile dokunmatik tablet POS arayüzü (Kategori listesi, ürün butonları, sepet, ödeme modalı).
  - Mobil Garson El Terminali (PWA): Garsonun masada telefonundan sipariş girmesi.
  - Basit KDS Mutfak/Barista Ekranı: Düşen siparişlerin yeşil/sarı/kırmızı zaman sayaçlarıyla listelenmesi.
- [ ] **Faz 3: Reçete ve Stok Düşüm Olay Motoru**
  - Sipariş onaylandığında veritabanındaki hammadde stoklarını otomatik eksilten arka plan tetikleyicisi.
- [ ] **Faz 5: Gerçek Sahada Pilot Deneme**
  - Butik bir kafede gerçek siparişlerle test ve geri bildirim döngüsü.
