# CafeERP geliştirme durumu

## Aşama 1 — Karar destek çekirdeğinin doğruluğu

29 Ekim 2026 tarihinde uygulanan değişiklikler:

- Eğitim sorgusunda ürün kalemleri adisyon bazında toplanır. Her adisyonun toplamı yalnızca bir kez sayılır; aynı tutarlı farklı adisyonlar korunur.
- Boş eğitim verisi veya yetersiz kronolojik eğitim/test ayrımı anlaşılır hata verir. Başarılı model paketi geçici dosyadan atomik olarak değiştirilir.
- Model ilk tahmin isteğinde yüklenir. Eksik veya bozuk model, satış raporlarının açılmasını engellemez; tahmin isteyen API çağrıları HTTP 503 döner.
- Boş satış raporları sıfır değerlerle döner. Son aktif güne geçiş yalnızca tarih verilmemişse yapılır; açıkça verilen boş bir tarih değiştirilmez. Geçersiz API tarihleri HTTP 422 döner.
- Rapor ve eğitim bağlantıları salt okunur açılır, hata durumunda da kapatılır.
- Hava durumu konumu `.env` üzerinden okunur. Eksik/geçersiz koordinatlar Kadıköy varsayılanına döner. Eksik hava durumu yanıtı canlı veri gibi gösterilmez.
- Telegram botu yalnızca `TELEGRAM_ALLOWED_USER_IDS` listesindeki kullanıcıların özel sohbetlerini işler. Liste boşsa polling başlamaz. Token parçaları ve token içerebilen ağ hatası metinleri konsola yazılmaz.

### Doğrulama

Proje kökünden:

```powershell
python -B -m unittest discover -s tests -v
python -B backend/app/ai/train_forecast.py
```

Testlerde geçici SQLite veritabanları ve sahte ağ yanıtları kullanılır; gerçek Telegram mesajı gönderilmez ve örnek işletme verisi değiştirilmez.

Yeniden eğitim: 37.310 sipariş, 2.703 saatlik kayıt, toplam 5.659.215 TL ciro. Son 30 gün test olarak ayrılır. Ciro modeli için MAE 567,44 TL/saat, RMSE 723,88 TL/saat, R² 0,621; trafik için MAE 3,22 sipariş/saat, R² 0,678.

Bu metrikler sentetik veri üzerindedir; gerçek işletmedeki başarıyı göstermez. Gerçekleşen satışlar SQL ile hesaplanır; talep ve stok tükenme saatleri tahmindir. Eğitim verisinde sipariş bulunmayan açık saatlerin sıfır talep olarak tamamlanması henüz uygulanmamıştır.

## Sıradaki aşamalar

1. **Sipariş ve stok altyapısı:** sürümlü şema geçişleri, menü/masa/adisyon servisleri, kuruş cinsinden para, ödeme ve iptal kayıtları, tek kaynaklı reçeteler ve stok hareketleri. Tekrarlanan istekler çift ödeme veya çift stok düşümü oluşturmamalı.
2. **İlk uçtan uca ekran:** tek masa için ürün ekleme → mutfağa gönderme → hazırlama → ödeme kapatma.
3. **Arayüzlerin genişletilmesi:** mobil garson PWA, canlı KDS, yönetici paneli.

## Mevcut sınırlar

- SQLite'ta altı uygulama tablosu vardır: `raw_materials`, `products`, `dining_tables`, `staff`, `orders`, `order_items`. `sqlite_sequence` SQLite'ın dahili tablosudur. `CODEX.md` ve eski mimari belgelerindeki bazı alanlar hedef tasarımdır.
- Reçeteler veri üretecinde ve JSON'da bulunur; SQL reçete tablosu ve gerçek stok hareketi henüz yoktur. Tahmin simülasyonundaki ortalama tüketim katsayıları gerçek ürün reçetelerinin yerine kullanılmamalıdır.
- Backend için kimlik doğrulama ve rol kontrolü henüz yoktur. Varsayılan sunucu yerel `127.0.0.1` adresinde çalışır; dış erişim öncesinde erişim kontrolü ve CORS yapılandırması tamamlanmalıdır.
- Telegram zamanlanmış sabah/akşam raporu göndermiyor; gelen mesajlara yanıt veriyor.
- Uygulama testleri `tests/` altındadır.
- Örnek veri üreteci mevcut tabloları yeniden oluşturur; canlı işletme verisinde çalıştırılmamalıdır.
