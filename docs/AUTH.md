# Personel girişi ve yetkiler — Aşama 4.1

31 Ekim 2026. API ve POS artık personel oturumu ister. İşletme tek kafe olarak
çalışır; şube/işletme ayrımı bu paketin kapsamında değildir.

## İlk kurulum ve mevcut kurulumun güncellenmesi

Mevcut veritabanını yedekleyin. Proje kökünde:

```powershell
docker compose build api frontend
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python scripts/create_admin.py
docker compose up -d --wait frontend
```

`004_staff_auth` yeni hesap, oturum, giriş denemesi ve denetim tablolarını ekler.
Geçmiş satış/stok kayıtlarını değiştirmez. `create_admin.py` kullanıcı adı,
ad soyad ve iki kez parola sorar. Parola terminalde görünmez; yalnızca `0–9`
rakamlarından oluşan 4–128 hane olmalıdır. Baştaki sıfırlar korunur.
Kullanıcı adı 3–50 karakter, küçük Latin harf/rakam/`_.-` içerir.
Parolayı komuta, `.env` dosyasına veya sohbet mesajına yazmanız gerekmez.

İlk hesap yalnızca hesap tablosu boşken açılır. Örnek `staff` tablosundaki
düz metin PIN'ler tarihsel veri olarak korunur; kimlik doğrulamada kullanılmaz.
Varsayılan yönetici, ortak parola veya herkese açık kayıt endpoint'i yoktur.

http://localhost:3000 adresinde giriş yapın. Yönetici sol menüde **Personel**
ekranından diğer hesapları açar, rol/aktiflik düzenler ve parola sıfırlar.
Kayıt değişikliği o personelin bütün cihazlardaki oturumlarını kapatır. Kendi
hesabını değiştiren yönetici de tekrar giriş yapar. Son aktif yönetici pasife
alınamaz veya başka role geçirilemez; sürümü eskimiş düzenleme 409 döner.

## Ortak kasada hızlı personel geçişi

Üst çubuktaki **Personel değiştir** → aktif hesabı seç → en az 4 karakterli
parolayı gir → **Geçiş yap** akışı kullanılır. Kullanıcı adı tekrar yazılmaz,
çıkış yapıp sayfa yüklenmesi beklenmez. Dokunmatik sayısal tuş takımı ve
sayısal klavye girişi bulunur; Enter ile onaylanabilir.

Yanlış parolada mevcut oturum korunur. Başarılı geçişte bu tarayıcının önceki
oturumu iptal edilir ve yeni personele ait oturum açılır. Yeni rol API'de
uygulanır; sonraki işlemler yeni personelin denetim kaydına yazılır. İşlem
gönderilirken geçiş düğmesi kilitlenir. Sonucu belirsiz yazmalar eski personele
bağlı kalır; yeni hesapla tekrar gönderilemez ve silinmez.

`GET /api/auth/switchable-staff`, oturumu açık personele yalnızca aktif
hesapların `id,username,name,role` bilgilerini verir. Parola doğrulaması normal
giriş endpoint'inde yapılır; parola saklama ve hatalı deneme sınırları aynıdır.
Mevcut parolalar otomatik değiştirilmez. Yönetici **Personel** ekranından yeni
en az 4 haneli sayısal parola belirleyebilir; ilk yönetici kurulumu da aynı
kuralı kullanır. Harf, boşluk, sembol ve `0–9` dışındaki rakam karakterleri
yeni parola kaydında API tarafından reddedilir. Önceden kaydedilmiş harfli
parolalar erişimi kaybetmemek için girişte kabul edilir; yönetici sayısal parola
belirlediğinde eski parola geçersiz olur ve açık oturumlar kapatılır.

## Rol matrisi

| İşlem | Yönetici | Kasiyer | Garson | Mutfak |
|---|---|---|---|---|
| Menü, masa, mutfak listesi | Evet | Evet | Evet | Evet |
| Adisyon okuma/açma, ürün/miktar, gönderme, taslak veya tüm adisyon iptali | Evet | Evet | Evet | Hayır |
| Gönderilmiş, hazırlığı başlamamış kalemi gerekçeyle iptal | Evet | Evet | Evet | Evet |
| Hazırlanıyor / hazır kalemi gerekçeyle iptal | Evet | Hayır | Hayır | Evet |
| Hazırlamaya başlama / hazır işaretleme | Evet | Hayır | Hayır | Evet |
| Hazır mutfak kartlarını temizleme | Evet | Hayır | Hayır | Evet |
| Tam ödeme kaydı | Evet | Evet | Hayır | Hayır |
| Stok/reçete ve finans/tahmin API'leri | Evet | Hayır | Hayır | Hayır |
| Personel listesi ve hesap yönetimi | Evet | Hayır | Hayır | Hayır |

Mutfak hesabı KDS ile açılır. Diğer personel mutfak akışını okuyabilir, hazırlık
butonlarını kullanamaz. Mutfaktaki durum yazma yanıtı mevcut adisyon anlık
görüntüsünü içerir; bu paket alan bazında fiyat gizleme uygulamaz. Garson ve
kasiyer hazırlığı başlayan ürünü iptal edemez; bu yetki mutfak/yöneticidedir.
Adisyonda aktif hazırlanıyor/hazır kalem varsa garson/kasiyer tüm adisyonu da
iptal edemez. Bu denetim adisyon kilidi altında yapılır; duruma bağlı ret 409
döner. Stok politikası `STOCK.md`'dedir.

KDS iptali `POST /api/kitchen/items/{item_id}/cancel` ile
`{tab_id,expected_version,reason}` alır. Mutfak rolü bu uçtan taslak kalemi
iptal edemez; tüm adisyon iptali veya ödeme yetkisi kazanmaz. İşlem geçmişi
`kitchen_cancel_item` olayı ve personel denetim kaydıyla saklanır.
`POST /api/kitchen/ready/clear` yalnızca mutfak/yöneticiye açıktır; hazır kartları
gizler, adisyonu veya stoğu değiştirmez. Kasiyer/garson bu işlemi yapamaz.

## Oturum ve istek sözleşmesi

- `POST /api/auth/login`: `{username,password}`; kullanıcı bilgisi döner,
  `cafeerp_session` çerezini ayarlar. Oturumun mutlak ömrü 12 saattir.
- `GET /api/auth/me`: güncel personel; giriş yok/sona ermiş/pasifse 401.
- `POST /api/auth/logout`: mevcut oturumu veritabanından siler ve çerezi temizler.
- Yönetici: `GET/POST /api/auth/staff`, `PATCH /api/auth/staff/{id}`.
  Oluşturma `{username,name,role,password}`, güncelleme
  `{name,role,is_active,expected_version,password?}` alır.
- Yazmalarda `X-CafeERP-Request: 1` zorunludur. Tarayıcı `Origin` gönderirse
  izinli kaynaklardan biri olmalıdır. POS istemcisi başlığı otomatik ekler.
- Sipariş/stok yazmalarında mevcut `Idempotency-Key` ve sürüm kuralları korunur.
  Başka personel aynı anahtarı kullanırsa 409 alır. İstemcinin gönderdiği
  `X-CafeERP-Actor` oturum personeliyle uyuşmazsa eski ekranın yazması 401 ile
  engellenir. Aktör kimliği oturumdan alınır; başlığa güvenilmez.
- API yanıtları `no-store` taşır. Yetki eksikliği 403'tür. Doğrulama hataları
  parola dahil istek girdilerini yanıtta geri yansıtmaz.

Parolalar rastgele tuzlu scrypt (`N=131072,r=8,p=1`) özetiyle saklanır.
Oturumda rastgele 256 bit belirteç kullanılır; veritabanında yalnızca SHA-256
özeti bulunur. Çerez `HttpOnly; SameSite=Strict; Path=/` taşır; localStorage
içine oturum belirteci/parola yazılmaz.

Aynı kullanıcı adına 15 dakikada 5 başarısız denemeden sonra giriş 429 olur.
Servis genelinde dakikada 60 deneme sınırı farklı adlarla taramayı sınırlar.
Sayaç veritabanında tutulur ve eşzamanlı isteklerde kilitlenir; yeniden başlatma
sınırı sıfırlamaz. Bu ilk sürümde hesap kilidi yönetici ekranından kaldırılmaz;
15 dakikalık pencerenin geçmesi beklenir. Eski denemeler ve süresi dolmuş
oturumlar giriş sırasında temizlenir.

Sipariş/stok komutunun sorumlu personeli, işlem türü, kaynağı ve tekrar anahtarı
`staff_audit` tablosuna iş verisiyle aynı transaction içinde yazılır. Başarısız
işlem iz bırakmaz; başarılı tekrar ikinci denetim veya finans/stok kaydı üretmez.
Hesap oluşturma/değişikliği ve başarılı girişler de kaydedilir. Bu kayıt için
henüz ayrı arayüz yoktur; geçmiş auth öncesi işlemlere personel uydurulmaz.

## Ağ ve HTTPS

Varsayılan Docker portları `127.0.0.1` ile sınırlı kalır. API ortam ayarları:

```dotenv
CAFE_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001
CAFE_COOKIE_SECURE=false
```

HTTP yerel geliştirme içindir. Gerçek cihazlarla kullanımdan önce HTTPS
sağlanmalı, `CAFE_COOKIE_SECURE=true` ve kesin arayüz origin'i ayarlanmalıdır.
Wildcard origin kullanılmaz. Next.js aynı kaynak proxy'si Cookie/Set-Cookie,
Origin ve güvenlik başlıklarını korur; tokenları tarayıcı JavaScript'ine açmaz.
Telegram kendi kullanıcı izin listesiyle çalışmaya devam eder.

Docker arayüzü 3000 portundayken yerel Next.js geliştirme sunucusu 3001'i
kullanabilir; bu iki yerel port varsayılan izin listesinde bulunur. Başka
port/adreste `İstek kaynağına izin verilmiyor` hatası alınırsa tam origin'i
`CAFE_ALLOWED_ORIGINS` ayarına ekleyip API konteynerini yeniden oluşturun.
`.env` içinde bu ayar açıkça tanımlıysa varsayılan listenin tamamının yerine geçer.

## Kesinti ve geçiş sınırları

Bekleyen POS yazması çıkışta silinmez. Oturum biterse aynı personel tekrar giriş
yapıp aynı anahtarla sonucu kontrol eder. Başka personelin bekleyen yazması
ekranda belirtilir ve o personel giriş yapana kadar yeni yazmalar engellenir.
401/403 yanıtı bekleyen kaydı otomatik temizlemez. Devre dışı bırakılan personele
ait belirsiz işlem yönetici tarafından veritabanı kayıtlarıyla mutabık tutulmalıdır.

Auth öncesi açık tarayıcılardaki bekleyen yazmaları yükseltmeden önce çözün;
eski anahtar kayıtları yeni personel bağıyla tekrar kullanılamaz. Auth öncesi
işlem geçmişi bu migration ile değiştirilmez.

E-posta ile parola kurtarma, MFA, kişisel parola değiştirme ekranı, vardiya/PIN
kilidi, boşta kalma kilidi ve gelişmiş güvenlik log ekranı sonraki işlerdir.
Bu adım Aşama 4'ün operasyonel ekranlarını veya pilot hazırlığını tamamlamaz.

## Doğrulama

63 backend testi, 7 frontend testi, TypeScript kontrolü ve Next.js üretim
derlemesi geçti. Rol testleri gerçek PostgreSQL üzerinde geçici şemalarla
çalışır; işletme verisine personel/satış eklemez. Garson → mutfak → kasiyer
akışında personel kayıtları, stok ve tek ödeme birlikte doğrulanır. Tarayıcı
erişim aracı bu oturumda kullanılamadığı için görsel kontrol beklemektedir.
Next.js üretim proxy'sinde giriş, Cookie/Set-Cookie aktarımı, güvenlik başlığı,
Origin reddi, personel oluşturma, rol reddi ve çıkış HTTP ile ayrıca doğrulandı.

Oturum/CSRF tasarım referansları:
[OWASP oturum rehberi](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[OWASP CSRF rehberi](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
