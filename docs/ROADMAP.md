# 🗺️ CafeERP Geliştirme Yol Haritası (Roadmap)

Aşağıdaki adımlar, projeyi sıfırdan çalışan bir MVP'ye ve ardından tam donanımlı bir AI ERP sistemine dönüştürmek için tasarlanmıştır.

---

## 📍 Faz 1: Çekirdek Veritabanı ve Örnek Veri Seti (Tamamlandı)
- [x] Proje vizyonu, hedef kitle ve mimari kararların netleştirilmesi.
- [x] Gerçekçi örnek veri simülatörünün hazırlanması (`data/generator/generate_sample_data.py`).
  - Menü, varyasyonlar, reçeteler, hammadde stoğu ve 6 aylık (37.000+) satış geçmişi.
- [x] FastAPI backend iskeleti ve AI API rotalarının kurulması (`backend/app/main.py`).
- [x] SQLite veritabanı bağlantısı (`data/sample_cafe.db`).

---

## 📍 Faz 2: POS, Masa Yönetimi & Mobil Garson Arayüzü (Frontend MVP)
- [ ] Next.js + Tailwind CSS + shadcn/ui ile dokunmatik POS ekranı.
- [ ] İnteraktif masa krokisi ve açık adisyon takibi.
- [ ] **Mobil Garson El Terminali (PWA):** Garsonun kendi telefonundan masada anlık sipariş alıp kasaya/mutfağa yollaması.
- [ ] Kategori, ürün filtreleme ve arama.
- [ ] Ürün varyasyon modalı (Süt tipi, boyut, ekstra shot).
- [ ] Sepet ve parçalı ödeme (Nakit / Kart / Alman usulü) akışı.
- [ ] Basit KDS (Mutfak / Çay Ocağı Ekranı) arayüzü ve WebSocket canlı durum güncellemesi.

---

## 📍 Faz 3: Reçete ve Stok Takip Motoru
- [ ] Satılan her sipariş için arka planda hammadde eksiltme mekanizması.
- [ ] Stok kritik seviye belirleme ve uyarı mantığı.
- [ ] Zayiat, ikram ve personel tüketim kayıtları.

---

## 📍 Faz 4: Yapay Zeka Katmanı (AI Brain - Tamamlandı)
- [x] **Talep ve Yoğunluk Tahmini:** LightGBM makine öğrenmesi modeli (`train_forecast.py` & `predictor.py`).
- [x] **Akıllı Stok Sipariş Asistanı:** Reçetelere göre saatlik hammadde tükenme (Burn-Rate) ve erken tedarik uyarısı.
- [x] **Canlı Hava Durumu Entegrasyonu:** Open-Meteo ile API anahtarsız otomatik hava tahmini (`weather_service.py`).
- [x] **Kural Tabanlı Uzman Karar Motoru (LLM-less):** %100 deterministik, halüsinasyonsuz, anında yanıt veren Türkçe NLU karar motoru (`decision_engine.py`).
- [x] **Telegram Asistanı ("Cepteki Müdür"):** Klavye butonları ve serbest soru yanıtlama desteği (`telegram_bot.py`).
- [x] **FastAPI REST Endpoint'leri:** Web ve mobil arayüz için `/api/ai/...` servisleri.

---

## 📍 Faz 5: İleri Düzey Entegrasyonlar & Test
- [ ] Pilot kafe testi (sahada gerçek bir butik kafede deneme).
- [ ] Offline-first (PWA) internet kesintisi dayanıklılığı.
- [ ] E-Fatura / ÖKC entegrasyonu hazırlığı.
