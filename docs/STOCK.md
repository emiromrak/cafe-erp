# Reçete ve stok motoru

31 Ekim 2026: Aşama 3 backend'i. Ürün reçeteleri SQL'de tek operasyonel kaynaktır.
Üretim tüketimi, satış tahmini ve geçmiş satış cirosu ayrı tutulur.
Aşama 4.1 itibarıyla stok/reçete uçları yönetici oturumu ister; yazmalara
`X-CafeERP-Request: 1` ve mevcut tekrar anahtarı eklenir. Kurulum: `AUTH.md`.

## Tüketim ve iptal politikası

- Taslak veya mutfağa gönderilmiş kalem stok tüketmez.
- `sent → preparing` geçişinde reçete okunur; miktarlar kalem adediyle çarpılır.
  Reçete sürümü, hammadde, birim ve miktarlar `item_materials` içine kopyalanır.
  Stok bakiyesi, hareket, adisyon sürümü ve hazırlık olayı tek transaction'dır.
- Reçetesi eksik veya stoğu yetersiz ürünün hazırlığı HTTP 409 ile engellenir.
  Birden fazla hammaddeden sonuncusu yetersiz olsa da bütün işlem geri alınır.
- `preparing → ready` ve ödeme kaydı tekrar stok düşmez.
- Hazırlıktan önce iptal stok etkilemez. Hazırlık başladıktan sonra iptalde
  mevcut tüketim `waste` olarak sınıflandırılır; stok otomatik geri eklenmez ve
  ikinci kez eksiltilmez. Gerekçe ilgili `tab_events` kaydından izlenir.
- Kullanılmamış gerçek malzemenin depoya dönüşü ayrı, gerekçeli `return`
  hareketidir. Hazırlanmış ürünün iptalini hammadde iadesi saymayın.
- Manuel malzeme bazlı ikram ve personel tüketimi `complimentary`/`staff`
  hareketidir. Ürün bazlı indirim veya ikram adisyonu bu API'nin kapsamı değildir.

## Miktar ve tekrar güvenliği

Stok, reçete, eşik ve birim maliyet `NUMERIC(20,6)`/Python `Decimal` kullanır.
API miktarları ondalık metin olarak döndürür. Miktarları hammaddenin kayıtlı
birimiyle gönderin; kg → gram gibi otomatik dönüşüm yapılmaz. En fazla altı
ondalık basamak ve 14 tam basamak desteklenir; negatif stok yasaktır.

Tüm yazmalarda `Idempotency-Key` zorunludur. Aynı anahtar ve gövde ilk başarılı
yanıtı döndürür. Reçete değiştirmede `expected_version` de zorunludur; ilk
tanımda 0 kullanılır. Ürün ve sıralı hammadde satır kilitleri aynı son stoğun
iki ayrı sipariş tarafından tüketilmesini engeller.

## Uçlar

| Metot | Yol | Davranış |
| --- | --- | --- |
| GET | `/api/inventory/materials` | Stoklar, birimler, maliyetler ve `is_critical` |
| GET | `/api/inventory/movements` | `material_id`, `after_id`, `before_id`, `order`, `limit` ile hareket defteri |
| POST | `/api/inventory/materials/{id}/movements` | Malzeme bazlı giriş veya tüketim |
| GET | `/api/recipes/{product_id}` | Reçete ve sürümü; tanımsız üründe sürüm 0 |
| PUT | `/api/recipes/{product_id}` | Yeni reçete sürümü ve geçmiş kaydı |

Örnek reçete gövdesi:

```json
{"expected_version":0,"reason":"İlk reçete","lines":[{"material_id":"rm_tea_leaf","quantity":"3.000000"},{"material_id":"rm_sugar_cube","quantity":"2"}]}
```

Örnek malzeme girişi:

```json
{"kind":"receipt","quantity":"1000","unit":"gram","reason":"Tedarik teslimatı"}
```

`receipt`/`return` stoğu artırır; `waste`/`staff`/`complimentary` azaltır.
Her tür için gövdede pozitif miktar gönderilir. `opening` ve `consume`
hareketlerini uygulama oluşturur. Defter kaydı silen/düzenleyen API yoktur.
Hazırlık iptali, tüketim hareketinin `disposition` alanında görünür.

Yönetici **Stok** ekranından bu işlemleri yapabilir. Yönetici dışındaki
rollerde menü görünmez ve API stok/reçete okuma-yazmalarını reddeder.
Stok bakiyesini doğrudan SQL ile değiştirmek hareket defterini bozar;
uygulamanın hareket API'si kullanılmalıdır.

## Yönetici ekranı — Aşama 4.2

- **Hammaddeler:** isim araması, yalnızca kritikler filtresi, stok/eşik/birim
  bilgisi. Kritik kararının kaynağı backend'dir. Bakiyeler 5 saniyede yenilenir.
- **Hareket ekle:** hammadde, giriş/iade/zayiat/personel tüketimi/ikram türü,
  pozitif miktar ve gerekçe. Birim seçilen hammaddeden alınır; birim dönüşümü
  yapılmaz. Depoya iade gerçek malzeme iadesidir, ödeme iadesi değildir.
- **Hareket defteri:** en yeni 50 kayıt, hammadde filtresi, eski kayıtları
  yükleme ve açıkça yenileme. Yeni API parametreleri `order=desc` ve
  `before_id`'dir; mevcut artan sıra/`after_id` sözleşmesi korunur.
- **Reçeteler:** ürün seçimi, bir ürün başına hammadde/miktar satırları,
  sürüm bilgisi ve gerekçeli kayıt. Aynı hammadde iki kez yazılamaz, boş
  reçete kaydedilemez. Ondalık virgül veya nokta kabul edilir; miktarlar
  float'a çevrilmeden, en fazla altı ondalık basamakla gönderilir.

Reçete başka bir cihazda değişirse sunucu 409 döner; form otomatik ezilmez.
**Güncel reçeteyi yükle** düğmesi sunucu sürümünü alıp mevcut taslağı yeniler.
Ürün veya alt sekme değiştirildiğinde kaydedilmemiş reçete taslağı saklanmaz.

Yazmadan önce tekrar anahtarı, gövde ve personel tarayıcıya kaydedilir.
Yanıt kaybolursa yeni yazmalar engellenir; stok formu kapanarak ortak
**Sonucu kontrol et** alanını erişilebilir bırakır. Reçete PUT isteği de
yenilemeden sonra aynı anahtar ve gövdeyle sürdürülebilir. Oturum biterse
aynı personel tekrar giriş yapar; başka personelin bekleyen yazması uygulanmaz.

Hammadde açma, kritik eşik/birim değiştirme ve reçete geçmişi görüntüleme
bu ekranın kapsamında değildir. Banka/ödeme iadesi ve ürün bazlı ikram da
ayrı iş paketleridir.

## Geçiş ve kurulum

Mevcut PostgreSQL verisini yedekledikten sonra proje kökünden:

```powershell
docker compose build api frontend
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python scripts/import_recipes.py
docker compose up -d --wait frontend
```

`003_inventory`, stokları altı ondalık basamağa dönüştürür ve mevcut bakiyeleri
birer açılış hareketiyle korur. Geçmiş satışlardan tüketim hesaplamaz.
Geçiş anında zaten hazırlanmış açık kalemler `inventory_legacy=true` olarak
işaretlenir; tüketim miktarı bilinmediğinden varsayımsal düşüm/iade üretilmez.

`import_recipes.py`, örnek JSON'daki 15 reçeteyi yalnızca boş ürün reçetelerine
aktarır. Mevcut reçeteyi değiştirmez; tanımsız ürün/hammaddede bütün aktarım
geri alınır. Farklı kafede reçeteler kendi ürün/hammadde kimlikleriyle API'den
tanımlanmalıdır. Yeni kurulumda önce `import_sqlite.py`, sonra bu betik çalışır.
SQLite aktarımı da yeni şemada stok açılış hareketlerini oluşturur.

## Tahmin ile gerçek stok ayrımı

Tükenme tahmini aynı SQL reçetelerini kullanır. Mevcut modelin grup tahmini,
son aktif 30 günün ürün satış paylarına dağıtılır; satış geçmişi olmayan
gruplarda eşit pay varsayımı bildirilir. Reçetesi eksik grup hesaplanmaz.
Modelin tahmin etmediği ürünler (örneğin demlik çay ve tatlılar) ayrıca
`forecast_warnings` içinde belirtilir. Tam menü yeterliliği iddia edilmez.

Simülasyon İstanbul saatine göre günün kalan saatlerini kullanır; içinde
bulunulan saatte yalnızca kalan dakika payı hesaplanır. Tahmin hiçbir stok
hareketi oluşturmaz. Kritik eşik uyarısı gerçek bakiyeden bağımsız olarak
korunur; kritik stok varken günlük brifing yeterli stok mesajı vermez.

## Doğrulama

Gerçek PostgreSQL geçici şemalarıyla 46 backend testi; tekrar istek, son stok
için eşzamanlı yarış, kısmi hata geri alma, reçete değişiminde tüketim kopyası,
iptal/zayiat ve defter mutabakatı doğrulanmıştır. Frontend'de 4 istek güvenliği
testi ve TypeScript kontrolü geçmiştir.

Aşama 4.2 sonrası toplam 64 backend ve 11 frontend testi geçti. Yeni
doğrulamalar: hareket defterinde azalan sıra/imleç/filtre, yönetici dışı
stok/reçete yazmalarının reddi, kesin miktar sınırları, yinelenen reçete
satırları ve yanıtı kaybolan PUT isteğinin kalıcı kayıttan tekrarı. Üretim
derlemesi başarılıdır. Tarayıcı aracı erişilemediğinden görsel kabul bekler.
Geçici şemada Next.js üretim proxy'si üzerinden stok girişi/tekrarı, hassas
bakiyeler, reçete PUT/tekrar/sürüm çatışması, defter imleci ve rol reddi HTTP
ile ayrıca doğrulandı; işletme verisine test hareketi eklenmedi.

Yerel geçişten önce `data/backups/` altında bir PostgreSQL yedeği alındı.
Bu klasör Git ve Docker build bağlamından hariçtir.
