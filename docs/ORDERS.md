# Adisyon ve ödeme API'si

Aşama 1, yerel geliştirme için tek masada tam tahsilat akışını sağlar.
Personel oturumu ve rol kontrolü Aşama 4.1 ile eklendi; kurulum ve istek
başlıkları `AUTH.md` dosyasındadır. API adresi `http://localhost:8000`, etkileşimli sözleşme
ve gövde şemaları `/docs` altındadır.

## Kurulum ve güncelleme

Mevcut verisi olan geliştirme ortamında proje kökünden:

```powershell
docker compose build api
docker compose run --rm api python -m alembic upgrade head
docker compose up -d --wait api
```

`002_tabs_payments`, ilk migration dosyasını ve geçmiş satışları değiştirmeden
kalem, ödeme, işlem geçmişi ve tekrar istek kayıtlarını ekler. Eski kapalı
adisyonlar `closed`, yeni tahsilatla kapananlar `paid` durumundadır.
Örnek veri aktarımı tekrar çalıştırılmaz. Otomatik downgrade veri kaybına
karşı kapalıdır; geçişten önce işletme verisi yedeklenmelidir.

## Temel kurallar

- Tüm yazma isteklerinde benzersiz `Idempotency-Key` başlığı zorunludur (1–128 karakter; harf, rakam, `_`, `.`, `:`, `-`). Yeni işlemde yeni anahtar kullanılır. Ağ hatasında aynı URL, gövde ve anahtarla tekrar gönderilir.
- Aynı anahtar ve aynı istek ilk başarılı yanıtı döndürür. Yanıt sonraki değişiklikleri içermez; güncel durum için adisyon yeniden okunur. Anahtarı farklı bir istekte kullanmak HTTP 409 döndürür. Anahtarlar işlem türleri arasında da ortaktır.
- Açılış dışındaki yazmalarda `expected_version` zorunludur. Başarılı her değişiklik sürümü bir artırır. HTTP 409 sürüm uyuşmazlığında güncel adisyon okunur, kullanıcının işlemi yeniden değerlendirilir ve yeni anahtarla gönderilir.
- Başarısız işlem bütün yazmaları geri alır ve tekrar anahtarını tüketmez. PostgreSQL adisyon satır kilidi, sürüm kontrolü ve tek ödeme kısıtı eşzamanlı işlemleri korur.
- Miktar 1–10.000 arasında tam sayıdır. Fiyat ve ürün adı sunucudan okunup kaleme kopyalanır; menüdeki sonraki değişiklikler mevcut kalemi etkilemez. İstemciden fiyat kabul edilmez.
- İşlem tutarları kuruş cinsinden tam sayıdır: `2535` = 25,35 TL. Mevcut `products.price` ve geçmiş satış alanları `NUMERIC(12,2)` olarak kalır; dönüşüm `Decimal` ile yapılır. Adisyon üst sınırı 999.999.999.999 kuruştur.
- Kalem akışı `draft → sent → preparing → ready` şeklindedir. Miktar yalnızca `draft` durumunda değişir. Tekrar gönderme yalnızca yeni `draft` kalemleri mutfağa yollar.
- Her aktif kalem gerekçeyle iptal edilebilir; kayıt silinmez. İptal edilen kalem toplama ve satış raporuna dahil edilmez. Tüm adisyonun gerekçeli iptali masayı boşaltır ve satış üretmez.
- Ödeme için en az bir aktif kalem bulunmalı, hepsi `ready` olmalı, toplam pozitif olmalı ve `amount_cents` güncel toplama eşit olmalıdır. İlk sürüm yalnızca tek seferde tam `cash` veya `card` kaydı destekler.
- Ödeme kaydı harici POS cihazından para çekmez veya mali fiş üretmez. Kapanmış adisyon değiştirilemez. Ödeme sonrası iade/ters kayıt ve parçalı ödeme bu sürümde yoktur.
- Aşama 3 güncellemesi: stok tüketimi hazırlık başlangıcında bir kez oluşur.
  Hazırlanmış ürün iptalinde tüketim zayiat sınıfına alınır; stok otomatik
  iade edilmez ve ikinci kez eksiltilmez. Reçete ve politika için `STOCK.md`.

## Uçlar

| Metot | Yol | İşlem |
| --- | --- | --- |
| POST | `/api/tabs` | `table_id` ile adisyon açma |
| GET | `/api/tabs?table_id=...` | Açık adisyonlar; masa filtresi isteğe bağlı |
| GET | `/api/tabs/{id}` | Kalemler, toplam, sürüm ve ödeme |
| POST | `/api/tabs/{id}/items` | `product_id`, `quantity`, `expected_version` ile kalem ekleme |
| PATCH | `/api/tabs/{id}/items/{item_id}` | Taslak miktarını değiştirme |
| POST | `/api/tabs/{id}/items/{item_id}/cancel` | `reason` ve sürümle kalem iptali |
| POST | `/api/tabs/{id}/submit` | Sürümle taslakları gönderme |
| PATCH | `/api/tabs/{id}/items/{item_id}/status` | `status` (`preparing`/`ready`) ve sürümle hazırlık |
| POST | `/api/tabs/{id}/payments` | `method`, `amount_cents`, sürüm ile kapatma |
| POST | `/api/tabs/{id}/cancel` | `reason` ve sürümle adisyon iptali |
| GET | `/api/tabs/{id}/events` | Sıralı işlem ve iptal geçmişi |
| GET | `/api/kitchen/items` | Açık adisyonların gönderilmiş/hazırlanan/hazır kalemleri |

HTTP 404 bulunamayan masa/adisyon/ürün/kalem; HTTP 422 geçersiz gövde veya
tutar sınırı; HTTP 409 sürüm, durum, tekrar anahtarı veya ödeme tutarı
uyuşmazlığıdır. Bilinmeyen gövde alanları reddedilir.

## Örnek akış

Gönderilmemiş satırda adet **− / ×adet / +** ile ayarlanır. 1 adetten **−**
ile 0'a düşürmek satırı gerekçe/onay istemeden kaldırır. API'de aynı davranış
`PATCH /api/tabs/{id}/items/{item_id}` için `quantity:0` ile uygulanır; satır
silinir, önceki miktar/ad/fiyat işlem geçmişinde korunur. Gönderilmiş,
hazırlanıyor veya hazır satırda miktar değiştirme/0'a indirme reddedilir;
çöp kutusu ile gerekçeli/onaylı iptal kullanılır.
Hazırlık başladığında garson/kasiyer için bu iptal de kapanır; hazırlanıyor ve
hazır kalemi mutfak/yönetici iptal edebilir. Tüm adisyon iptali de aynı koşulu
denetler; böyle bir kalem varken garson/kasiyer toplu iptal yapamaz. Güncel
durum sunucuda transaction içinde denetlenir; eski ekran kuralı aşamaz.

Hazır kalemler otomatik süreyle gizlenmez. Hazır sütunundaki **Temizle**,
mutfak/yönetici tarafından o anda görünen hazır kartları listeden kaldırır
(tek istekte en fazla 1.000 kart). `POST /api/kitchen/ready/clear`,
`{item_ids:[...]}` ve `Idempotency-Key` alır. İşlem `kitchen_cleared` olayıyla
kalıcı saklanır; sayfa yenilemede geri gelmez, diğer ekranlar ilk yenilemede
eşitlenir. Tıklama sonrasında yeni hazır olan veya istekte yer almayan kalemler
temizlenmez. Bekleyen, hazırlanan, iptal edilmiş ve kapanmış adisyondaki
kalemler atlanır. Tekrar istek ikinci temizlik oluşturmaz.

Adisyon satırı `ready` olarak kalır; adisyon sürümü, hesap, ödeme ve stok
değişmez. Temizleme, iptal veya tüm adisyonu kapatma işlemi değildir.

Menüden aynı ürün tekrar eklendiğinde adı/fiyatı aynı olan gönderilmemiş
satırın miktarı artırılır (iki çay tek satırda ×2). Gönderilmiş, hazırlanıyor,
hazır veya iptal edilmiş satır değiştirilmez; yeni taslak satır açılır. Fiyat/ad
değişmişse de yeni satır açılarak eski satış kopyası korunur. Satır başına
10.000 adet sınırı ve tekrar anahtarı kuralları geçerlidir.

Mutfak kartındaki **Ürünü iptal et**, gerekçe ve açık onay isteyen bir uyarı
açar; **Vazgeç** kayıt oluşturmaz. Onaylanan iptal kalemin bütün miktarını
hesaptan çıkarır ve KDS listesinden kaldırır. Hazırlık başlamadıysa stok
değişmez; başladıysa tüketim zayiat sayılır ve geri eklenmez. Son kalem iptal
edildiğinde adisyon açık kalır; tüm adisyonu kapatma servis personelindedir.

`GET /api/tables` ve `GET /api/products` ile gerçek kimlikler alınır.
Aşağıdaki örnekte masa/ürün kimlikleri temsildir; çağrılar gerçek kayıt üretir.
Her adım için yeni bir `Idempotency-Key` kullanılır. Yanıttaki `id`, kalem `id`
ve `version` sonraki adımda kullanılmalıdır.
Önce yönetici hesabıyla giriş yapıp oturum çerezini isteklere ekleyin; tüm
yazmalarda `X-CafeERP-Request: 1` gerekir. Tek hesapla bu örneğin tamamını
yalnızca yönetici çalıştırabilir; diğer roller kendi adımlarını yapar.

```text
POST /api/tabs
{"table_id":"masa-kimliği"}

POST /api/tabs/{id}/items
{"expected_version":0,"product_id":"ürün-kimliği","quantity":2}

POST /api/tabs/{id}/submit
{"expected_version":1}

PATCH /api/tabs/{id}/items/{item_id}/status
{"expected_version":2,"status":"preparing"}

PATCH /api/tabs/{id}/items/{item_id}/status
{"expected_version":3,"status":"ready"}

POST /api/tabs/{id}/payments
{"expected_version":4,"method":"cash","amount_cents":5070}
```

Son örnekte 5.070 kuruş, iki adet 25,35 TL ürün varsayar; gerçek tutar
adisyon yanıtındaki `total_cents` değerinden alınır.

## Satış raporu ve geçmişle ilişki

Ödeme transaction'ı içinde `tab_payments` kaydı, benzersiz `TAB_...` satış
kimliğiyle `orders` ve iptal edilmemiş kalemlerle `order_items` kaydı oluşur;
adisyon kapanır, sürüm ve olay kaydı yazılır. Bu adımların herhangi biri
başarısızsa tamamı geri alınır. `tab_payments.tab_id` ve `order_id` benzersizdir.
Böylece mevcut AI satış raporu ve eğitim sorguları yeni satışları da tek kez
görür. Ödenmemiş/iptal edilmiş adisyonlar ciroya eklenmez.

Satış zamanı açıkça `Europe/Istanbul` saat diliminde kaydedilir. Yeni satışta
`orders` içindeki eski personel ve hava alanları henüz doldurulmaz;
personel sorumluluğu Aşama 4.1 itibarıyla `staff_audit` kaydında tutulur.

## Doğrulama

```powershell
docker compose run --rm --no-deps --volume "${PWD}:/app:ro" api python -B -m unittest discover -s tests -v
```

Adisyon testleri gerçek PostgreSQL'de geçici şemalar açar, Alembic zincirini
uygular ve şemaları sonunda kaldırır. Tutar/fiyat kopyası, nakit/kart, iptal,
hata halinde geri alma, geçmiş verinin korunması, aynı/farklı anahtarlı
eşzamanlı ödeme ve düzenleme yarışları doğrulanır. İşletme verisine test
adisyonu veya test ödemesi eklenmez.
