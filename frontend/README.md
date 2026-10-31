# CafeERP POS arayüzü

Next.js App Router, React, TypeScript, Tailwind CSS ve shadcn/ui yapısına uygun
Radix tabanlı button/dialog bileşenleri. İlk işletme modeli masa servisidir.

## Docker ile kullanım

Proje kökünden, PostgreSQL kurulumu ve `alembic upgrade head` tamamlandıktan sonra:

```powershell
docker compose up -d --build --wait frontend
```

Arayüz: http://localhost:3000 — API sözleşmesi: http://localhost:8000/docs
Frontend ve API portları yalnızca yerel bilgisayara açılır.
İlk yönetici hesabını proje kökünde `docker compose run --rm api python scripts/create_admin.py`
ile açın. Kullanıcı adı/parola girişinden sonra yöneticide **Personel** ekranı
görünür. Roller ve HTTPS ayarları: `../docs/AUTH.md`.

## Yerel geliştirme

Node.js 24 ile, `frontend/` içinde:

```powershell
npm ci
npm run dev
```

Varsayılan API `http://127.0.0.1:8000` adresidir. Farklı adres için sunucuyu
başlatmadan önce `API_BASE_URL` ayarlanır. Bu değişken yalnızca Next.js
sunucusunda kullanılır; tarayıcı aynı origin'deki `/api` uçlarına erişir.
API yönlendirmesi cache kullanmaz ve tekrar anahtarını korur. Windows'ta
gözlenen Turbopack alt süreç hatası nedeniyle dev/build Webpack kullanır.
Docker arayüzü 3000'i kullanıyorsa Next.js yerelde 3001'e geçebilir. API'nin
varsayılan kaynak listesi her iki portun localhost/127.0.0.1 adreslerini kabul
eder; özel port/adresler `CAFE_ALLOWED_ORIGINS` ile açıkça tanımlanır.

```powershell
npm run typecheck
npm test
npm run build
npm start
```

## Kullanım ve hata davranışları

- Alan filtresinden masa seçin; mevcut adisyon açılır. Boş masada `Adisyon aç`
  düğmesiyle başlayın. Yalnızca masayı görüntülemek kayıt oluşturmaz.
- Kategori veya aramayla ürünü bulun. Gönderilmemiş kalemin miktarını değiştirin;
  iptal için gerekçe girin. Yeni ürünler ayrı kalem olarak eklenir.
- `Mutfağa gönder`, yalnızca gönderilmemiş kalemleri yollar. Mutfak sekmesinden
  sırayla `Hazırlamaya başla` ve `Hazır işaretle` işlemlerini yapın.
- Tüm aktif kalemler hazır olduğunda nakit/kart tahsilatını onaylayıp kaydedin.
  Kesin toplam ve ödeme doğrulaması backend'den gelir. UI yalnızca para gösterimini yapar.
- Sunucu verileri 5 saniyede yenilenir. Kaydedilmiş adisyon sayfa yenilemesinden
  sonra masa listesinden tekrar açılabilir. Bağlantı yokken yeni yazmalar engellenir.
- Sonucu belirsiz kalan yazma, anahtarı ve gövdesiyle tarayıcının localStorage
  alanında saklanır. `Sonucu kontrol et` aynı isteği tekrar gönderir; sonuç
  çözülene kadar yeni yazmalar engellenir. Bu kayıt offline sipariş kuyruğu değildir.
- Sürüm uyuşmazlığında ekran güncellenir; kullanıcının işlemi yeniden değerlendirmesi
  gerekir. İstek otomatik olarak yeni sürümle uygulanmaz.
- Garson/kasiyer adisyon işlemlerini yapar, mutfak/yönetici hazırlığı ilerletir,
  kasiyer/yönetici ödeme kaydeder. Rol sınırları API'de de uygulanır.
- Oturum bitince giriş ekranı açılır; belirsiz yazma silinmez. Aynı personel
  tekrar giriş yaparak sonucu kontrol eder. Başka personele ait kayıt ekranda belirtilir.
- Ortak kasada **Personel değiştir** ile hesap seçip parolayla devam edin.
  Sayısal tuş takımı dokunmatik giriş içindir; harfli parolalar da desteklenir.
  Parola alt sınırı 4 karakterdir. Geçişte önceki tarayıcı oturumu iptal edilir.

## İzole tarayıcı testi

Proje kökünden:

```powershell
docker compose run --rm --no-deps --publish 127.0.0.1:8001:8000 --volume "${PWD}:/app:ro" api python -B tests/serve_ui_fixture.py
```

Ayrı terminalde `frontend/` içinde:

```powershell
$env:API_BASE_URL='http://127.0.0.1:8001'
npm run dev
```

Geçici şemadaki Masa 1 ve Çay ürünüyle açılış → ekleme → miktar 2 → gönderme
→ hazırlanıyor → hazır → 50,70 TL nakit ödeme → masa boşaltma denenebilir.
Gerekçeli iptal de ayrı adisyonla doğrulanır. Normal Ctrl+C kapanışında test
şeması temizlenir. Zorla öldürme halinde `test_tabs_...` şeması kalabilir;
işletme şemasında test kaydı oluşturulmaz.
Bu geçici şemaya özel giriş: `testadmin` / `Test-parolasi-2026!`.
Bu hesap işletme veritabanında bulunmaz; gerçek kurulumda kullanılmaz.

Tablet için 1024×768, dar ekran için 390×844 yerleşimleri kontrol edilir.
Bu sürüm mobil garson PWA, offline çalışma, parçalı ödeme,
ürün varyasyonu ve banka POS entegrasyonu içermez. Aşama 3 güncellemesiyle
hazırlık başlatmak SQL reçetesinden gerçek stok tüketir; stok politikası
`../docs/STOCK.md` dosyasındadır. Stok/reçete yönetimi şimdilik API'dedir.

Bekleyen yazmalar her istek için ayrı localStorage kaydı kullanır; birden
fazla sekme birbirinin tekrar anahtarını ezmez. Veri okumaları sıraya alınır.
İlk açılışta bağlantı uyarısı yerine bağlanma durumu gösterilir.
