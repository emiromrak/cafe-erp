# CafeERP geliştirme durumu

## PostgreSQL geçişi

Uygulama ve model eğitimi PostgreSQL kullanır. `migrations/` Alembic şemasını,
`scripts/import_sqlite.py` ise eski örnek SQLite verisinin tek seferlik güvenli
aktarımı için kullanılır. Menü ve masa uçları `/api/categories`, `/api/products`
ve `/api/tables` adreslerindedir. Masa doluluğu `open_tabs.closed_at` alanı boş
olan adisyonlardan türetilir; adisyon oluşturma ve ödeme API'leri `ORDERS.md` dosyasında belgelenmiştir.
Geçmiş siparişler açık adisyon sayılmaz. Bağlantı ve kurulum için `DOCKER.md`.

## Tamamlanan çalışma — Karar destek çekirdeğinin doğruluğu

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

Testlerde PostgreSQL üzerinde geçici şemalar ve sahte ağ yanıtları kullanılır; gerçek Telegram mesajı gönderilmez ve örnek işletme verisi değiştirilmez.

Yeniden eğitim: 37.310 sipariş, 2.703 saatlik kayıt, toplam 5.659.215 TL ciro. Son 30 gün test olarak ayrılır. Ciro modeli için MAE 567,44 TL/saat, RMSE 723,88 TL/saat, R² 0,621; trafik için MAE 3,22 sipariş/saat, R² 0,678.

Bu metrikler sentetik veri üzerindedir; gerçek işletmedeki başarıyı göstermez. Gerçekleşen satışlar SQL ile hesaplanır; talep ve stok tükenme saatleri tahmindir. Eğitim verisinde sipariş bulunmayan açık saatlerin sıfır talep olarak tamamlanması henüz uygulanmamıştır.

## Sıradaki aşamalar

Ana kapsam ve çıkış ölçütleri `ROADMAP.md` dosyasındadır. Güncel sıra:

Aşama 1 tamamlandı: `002_tabs_payments` migration'ı, adisyon/kalem/hazırlık/iptal/ödeme API'leri ve işlem geçmişi eklendi. Para kuruşla tutulur; fiyat satış anında kopyalanır. Her yazma isteğinde tekrar anahtarı, açılış dışında adisyon sürümü zorunludur. Satır kilitleri ve tek ödeme kısıtı eşzamanlı işlemleri korur. Ödeme, rapor satış kaydı ve adisyon kapanışı tek transaction'dır.

Kullanım, güncelleme komutları ve sınırlar: `ORDERS.md`. PostgreSQL üzerinde yeni adisyon testleri dahil toplam 34 test geçti; geçici şemalar kullanıldı, işletme verisine test satışı eklenmedi.

Yerel Docker API imajı yenilendi ve `002_tabs_payments` geçişi uygulandı.
Geçiş öncesi/sonrası 37.310 sipariş ve 5.659.215,00 TL geçmiş ciro aynı kaldı.
Çalışan serviste adisyon, mutfak ve masa okuma uçları HTTP 200 döndü;
ödeme uçları OpenAPI sözleşmesinde doğrulandı. Eğitim veri okuyucusunun
kendi oluşturduğu bağlantı havuzu da işlem sonunda kapatılır.

Aşama 2 tamamlandı: `frontend/` altında masa/menü/adisyon, temel KDS, gerekçeli iptal ve tam ödeme ekranları eklendi. Sunucu toplamı, tekrar anahtarı ve sürüm kuralları korunur. Tarayıcıda geçici PostgreSQL şemasıyla 2 çay / 50,70 TL tam nakit ödeme ve gerekçeli adisyon iptali doğrulandı. Üç istek güvenliği testi ve TypeScript kontrolü geçti. Docker kurulum ve test tarifi `../frontend/README.md` dosyasındadır.

Sıradaki aşamalar:
31 Ekim 2026: Aşama 3 backend'i tamamlandı. `003_inventory`, 15 örnek SQL
reçetesi, hazırlık başlangıcında atomik tüketim, zayiat/iade hareketleri ve
reçete sürümleri eklendi. 46 backend ve 4 frontend testi geçti; TypeScript ve
üretim derlemesi doğrulandı. İnceleme bulguları `REVIEW_2026-10-31.md`, stok
politikası ve kurulum `STOCK.md` dosyasındadır.

1. **Sıradaki — Aşama 4:** kimlik doğrulama/roller, yetkili stok yönetim ekranları; mobil garson, canlı KDS ve gelişmiş ödeme.
2. **Aşama 5:** yedekten dönüş, kasa/stok mutabakatı, kesinti davranışı ve gerçek veriyle pilot.

## Mevcut sınırlar

- Eski SQLite kaynağı altı uygulama tablosu içerir. `CODEX.md` ve eski mimari belgelerindeki bazı alanlar hedef tasarımdır.
- SQL reçeteleri operasyonel kaynaktır; JSON yalnızca ilk örnek aktarım kaynağıdır. Ürün bazlı ikram ve ayrı stok/reçete yönetim ekranı henüz yoktur; malzeme hareketleri API'den kaydedilir.
- Backend için kimlik doğrulama ve rol kontrolü henüz yoktur. Varsayılan sunucu yerel `127.0.0.1` adresinde çalışır; dış erişim öncesinde erişim kontrolü ve CORS yapılandırması tamamlanmalıdır.
- Telegram zamanlanmış sabah/akşam raporu göndermiyor; gelen mesajlara yanıt veriyor.
- Uygulama testleri `tests/` altındadır.
- Örnek veri üreteci mevcut tabloları yeniden oluşturur; canlı işletme verisinde çalıştırılmamalıdır.
