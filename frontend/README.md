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

Tablet için 1024×768, dar ekran için 390×844 yerleşimleri kontrol edilir.
Bu sürüm mobil garson PWA, offline çalışma, erişim kontrolü, parçalı ödeme,
ürün varyasyonu, stok düşümü ve banka POS entegrasyonu içermez.
