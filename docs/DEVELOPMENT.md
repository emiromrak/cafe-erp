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

1. **Devam eden — Aşama 4:** 4.1 personel girişi/roller ve 4.2 stok/reçete yönetimi uygulandı. **Sıradaki 4.3** yönetici özeti; ardından mobil garson/canlı KDS ve gelişmiş ödeme. 4.2 görsel kabulü bekler.
2. **Aşama 5:** yedekten dönüş, kasa/stok mutabakatı, kesinti davranışı ve gerçek veriyle pilot.

## Mevcut sınırlar

- Eski SQLite kaynağı altı uygulama tablosu içerir. `CODEX.md` ve eski mimari belgelerindeki bazı alanlar hedef tasarımdır.
- SQL reçeteleri operasyonel kaynaktır; JSON yalnızca ilk örnek aktarım kaynağıdır. Yönetici stok/reçete ekranları vardır; ürün bazlı ikram, hammadde tanımı/eşik düzenleme ve reçete geçmişi arayüzü henüz yoktur.
- Backend personel oturumu ve rol kontrolü uygular. İlk yönetici `scripts/create_admin.py` ile oluşturulur. Varsayılan sunucu yereldir; çok cihazlı kullanım öncesinde HTTPS ve güvenli çerez/origin ayarları gerekir. Ayrıntılar `AUTH.md`.
- Telegram zamanlanmış sabah/akşam raporu göndermiyor; gelen mesajlara yanıt veriyor.
- Uygulama testleri `tests/` altındadır.
- Örnek veri üreteci mevcut tabloları yeniden oluşturur; canlı işletme verisinde çalıştırılmamalıdır.

## Aşama 4.1 — 31 Ekim 2026

`004_staff_auth`, scrypt parola özetleri, iptal edilebilir 12 saatlik oturum,
yönetici/kasiyer/garson/mutfak rolleri, giriş/çıkış ve personel yönetimi eklendi.
Ödeme kasiyer/yöneticiye, hazırlık mutfak/yöneticiye, stok/reçete ve finans
API'leri yöneticiye sınırlandı. İş yazmaları personelle birlikte atomik
denetim kaydına alınır; tekrar anahtarı farklı personelde kullanılamaz.

59 backend ve 6 frontend testi, TypeScript ve üretim derlemesi geçti. Geçici
şemada çalışan Next.js proxy'sinde giriş, Cookie/Set-Cookie, güvenlik başlığı,
Origin reddi, hesap açma, rol dışı erişim ve çıkış HTTP üzerinden doğrulandı.
Tarayıcı erişim aracı kullanılamadığından görsel doğrulama bekler. İşletme
parolası varsayılmadı; ilk yönetici kurulumu terminalde kullanıcıya aittir.

Ortak POS güncellemesi: parola alt sınırı tüm oluşturma/sıfırlama/kurulum
akışlarında 4 karaktere indirildi. Personel seçimi, dokunmatik sayısal giriş ve
sayfa yenilemeden oturum değiştirme eklendi. Eski oturum iptal edilir; yanlış
parola mevcut oturumu bozmaz. Eski istekten geciken 401 yeni oturumu kapatmaz.
Bu güncellemeyle 62 backend ve 7 frontend testi bulunur.

Sayısal parola güncellemesi: yeni hesap, parola sıfırlama ve ilk yönetici
kurulumunda yalnızca `0–9` rakamlarından oluşan 4–128 haneli parola kabul
edilir. Baştaki sıfırlar korunur. Eski harfli parolalar yönetici sayısal parola
belirleyene kadar girişte kabul edilir; mevcut hesaplara erişim kaybolmaz.
Bu kuralla birlikte 63 backend ve 7 frontend testi bulunur.

## Aşama 4.2 — Stok ve reçete ekranları

Yöneticiye özel **Stok** menüsü; hammadde/kritik liste, malzeme hareket formu,
en yeniden başlayan sayfalı defter ve sürüm denetimli reçete düzenleme eklendi.
POS ve stok yazmaları ortak işlem kilidi/kaydı kullanır; PUT isteği yenilemeden
sonra sürdürülebilir. Miktarlar float'a çevrilmez. Toplam 64 backend ve 11
frontend testi, TypeScript ve üretim derlemesi geçti. Tarayıcı erişimi olmadığı
için görsel/dokunmatik kabul bekler. Yeni migration gerekmez.
İzole şemada Next.js proxy'sinden stok/reçete yazmaları, tekrarlar, sürüm
çatışması, hareket sayfalama ve rol reddi HTTP üzerinden doğrulandı.

## KDS iptali ve taslak miktar birleştirme

Mutfak kalemine gerekçeli ve onay uyarılı iptal eklendi. Mutfak rolü gönderilmiş,
hazırlanıyor veya hazır kalemi iptal edebilir; taslak/tüm adisyon/ödeme yetkisi
değişmez. Hazırlanmış tüketim zayiat işaretlenir ve stok geri eklenmez.
Menüde tekrar seçilen ürün, aynı ad/fiyattaki taslağın miktarını artırır;
gönderilmiş satır veya farklı fiyat kopyası değiştirilmez. Satır limiti,
toplam tutar, sürüm ve tekrar anahtarı korumaları aynı transaction'dadır.
Bu güncellemeyle 68 backend ve 11 frontend testi, TypeScript kontrolü ve
üretim derlemesi geçti. Taslak birleştirme/tekrar, fiyat kopyası, miktar limiti,
mutfak rolünde gerekçeli iptal ve hazırlık sonrası zayiat doğrulandı.

Hazır KDS kartlarının bir dakikalık otomatik gizlenmesi kaldırıldı. Bunun
yerine mutfak/yönetici için **Temizle** eklendi. İstekteki hazır kartlar
`kitchen_cleared` olaylarıyla kalıcı gizlenir; yeni hazır olan kartlar aynı
isteğin tekrarından etkilenmez. Adisyonun `ready` durumu/sürümü, ödeme ve stok
değişmez. Yeni migration gerekmez; mevcut olay tablosu kullanılır.
71 backend ve 11 frontend testi, TypeScript ve üretim derlemesi geçti.
Manuel temizlemede adisyon/ödeme/stok korunması, tekrar istek, yeni hazır
olan kartın korunması ve mutfak/yönetici yetkisi doğrulandı.

Taslak satırda **−** 1'den 0'a inebilir; satır gerekçesiz kaldırılır, önceki
miktar/ad/fiyat olay kaydında korunur. Taslakta çöp kutusu gizlidir. Gönderilmiş
kalemler miktar 0 ile silinemez; gerekçeli/onaylı iptal korunur.
73 backend ve 11 frontend testi, TypeScript kontrolü ve üretim derlemesi geçti.

Hazırlığı başlayan ürünün iptali mutfak/yöneticiye sınırlandı. Garson/kasiyer
yalnızca hazırlığı başlamamış ürünleri iptal eder. Hazırlanıyor/hazır kalem
varken tüm adisyon iptali de engellenir. Denetim iki kalem iptal ucunda ve
toplu iptalde, adisyon kilidi altında uygulanır; arayüzde düğmeler uyarlanır.
75 backend ve 13 frontend testi, TypeScript ve üretim derlemesi geçti.
