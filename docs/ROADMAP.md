# 🗺️ CafeERP Geliştirme Yol Haritası

30 Ekim 2026 tarihinde mevcut kod ve bağımlılıklara göre güncellendi.
Geliştirme sırasının ana kaynağı bu belgedir. Eski faz numaraları yerine aşağıdaki aşamalar izlenir. İşaretli maddeler mevcut uygulamayı, boş maddeler planlanan işleri gösterir.

## İşletme modeli kararı

Ürün hem garsonla masa servisi yapan hem de kasada sipariş/peşin ödeme alan
kafelere sunulacaktır. İlk uygulanacak model **masa servisi** olarak seçildi.
Aşama 2 akışı: masa seç → ürün ekle → mutfağa gönder → hazırla → ödeme kaydet
→ adisyonu kapat. Aynı masaya servis boyunca yeni ürün eklenebilir.

Kafeye göre çalışma modelinin seçilebilmesi hedeflenir; kasada peşin ödeme
desteği henüz uygulanmamıştır. Bu destek eklenirken hazırlık ve ödeme durumları
ayrı izlenecek; ödeme alınmış sipariş mutfakta hazırlanmaya devam edebilecektir.
Mevcut backend'in yalnızca hazır kalemlerden tam ödeme alma kuralı şimdilik
masa servisi için korunur. Mod seçimi ve ödeme öncesi hazırlık kuralının
uyarlanması, self-servis geliştirmesinin ayrı kabul ölçütleriyle ele alınır.

## Tamamlanan temel

- [x] Menü, masa, hammadde ve yaklaşık 37 bin siparişlik sentetik örnek veri.
- [x] FastAPI; satış, tahmin, stok simülasyonu, brifing ve sorgu API'leri.
- [x] LightGBM modeli, Open-Meteo entegrasyonu ve deterministik Türkçe karar motoru.
- [x] Yetkili kullanıcılarla sınırlı Telegram soru-cevap asistanı.
- [x] Ciro toplama, model yükleme ve hata yönetimi düzeltmeleri; çekirdek ve API testleri.
- [x] Docker Compose ve Dev Container geliştirme ortamı.
- [x] PostgreSQL geçişi, ilk Alembic geçişi ve SQLite veri aktarım betiği.
- [x] Kategori, ürün ve masa listeleme API'leri; açık adisyona göre masa doluluğu.

Adisyon ve ödeme API'leri Aşama 1 kapsamında eklendi. POS ve basit mutfak arayüzü Aşama 2 kapsamında eklendi. Henüz SQL reçeteleri ve gerçek stok hareketleri yoktur. Stok tükenme simülasyonu gerçek stok düşümü yapmaz. Tahmin başarısı sentetik veri üzerinde ölçülmüştür; saha doğrulaması bekler.

## Aşama 1 — Adisyon ve ödeme backend'i (tamamlandı)

Amaç: tek masanın hesabını API üzerinden güvenilir biçimde açıp kapatmak.

- [x] İlk migration dosyasını değiştirmeden yeni Alembic geçişleriyle adisyon kalemleri, ödeme ve iptal kayıtlarını eklemek; geçmiş satışlarla yeni adisyonların ilişkisini tanımlamak.
- [x] Masa için adisyon açma, açık adisyonu okuma, ürün ekleme, miktar değiştirme ve kalem iptal etme servisleri.
- [x] Fiyatı sunucudan almak ve satış anındaki fiyatı kalemde saklamak. Yeni işlem tutarlarını kuruş cinsinden tam sayı ile yönetmek; mevcut `NUMERIC` fiyatlarla dönüşümü tanımlamak.
- [x] Mutfağa gönderme, hazırlanıyor ve hazır durumlarını; izin verilen geçişleri ve işlem geçmişini tanımlamak.
- [x] İlk sürümde tek seferde nakit veya kart tahsilatı kaydetme, adisyon kapatma ve masayı boşaltma. Bu kayıt harici POS cihazından ödeme çekmez.
- [x] Tekrarlanan isteklerin ikinci adisyon, ikinci kalem veya ikinci ödeme oluşturmamasını sağlamak; eşzamanlı değişiklikleri veritabanı işlemleri ve kısıtlarla korumak.
- [x] Kapanan satışın raporlara yalnızca bir kez yansımasını ve ödeme/iptal geçmişinin korunmasını sağlamak.
- [x] PostgreSQL testleriyle tutar doğruluğu, geçersiz durum geçişleri, tekrar istekler, eşzamanlı işlemler ve hata halinde geri almayı doğrulamak.

**Çıkış ölçütü:** API üzerinden masa aç → ürün ekle → mutfağa gönder → hazırla → ödeme kaydet → adisyon kapat akışı çalışır. Aynı isteğin tekrarı çift kayıt oluşturmaz; kapanan hesap satış raporuyla tutarlıdır.

## Aşama 2 — İlk uçtan uca POS ve basit mutfak ekranı (tamamlandı)

İlk arayüz masa servisine odaklanır: masa listesi → masa adisyonu ve menü →
mutfak ekranı → servis sonrası tam ödeme. Mobil garson PWA bu aşamanın dışında,
Aşama 4 kapsamındadır.

- [x] `frontend/` altında Next.js, Tailwind CSS ve shadcn/ui ile uygulama temeli.
- [x] Masa listesi, açık adisyon, kategori/ürün seçimi, miktar düzenleme ve hesap toplamı.
- [x] Mutfağa gönderme ve basit KDS üzerinden hazırlık durumu değiştirme; ilk sürümde periyodik yenileme yeterlidir.
- [x] Nakit/kart ödeme ve hesap kapatma ekranı; API hataları, bekleme ve yeniden deneme durumları.
- [x] Masaüstü/tablet kullanımını ve ilk uçtan uca akışı doğrulamak; tutarların kaynağı backend olmalıdır.

**Çıkış ölçütü:** Bir masanın sipariş ve ödeme akışı tarayıcıdan tamamlanır; sayfa yenilenince adisyon durumu kaybolmaz. Bu aşama yerel geliştirme içindir; dış erişim ve gerçek işletme kullanımı Aşama 4 ve 5 koşullarına bağlıdır.

## Aşama 3 — Reçeteler ve gerçek stok hareketleri (sıradaki iş)

- [ ] Ürün reçetelerini SQL'de tek kaynakta toplamak; birim ve miktarları kesin hassasiyetle tanımlamak.
- [ ] Üretime gönderme/hazırlama, iptal, ikram ve zayiat için stok etkisinin hangi olayda oluşacağını belirlemek ve belgelemek. Ödeme kapatmayı tüketimle otomatik eşitlememek.
- [ ] Stok giriş, tüketim, iade ve zayiat hareketlerini izlenebilir kayıtlarla uygulamak; işlem anındaki reçete miktarlarını saklamak.
- [ ] Tekrar isteklerde çift stok düşümünü önlemek; stok hareketini ilgili iş olayıyla atomik veya güvenilir yeniden işleme mekanizmasıyla bağlamak.
- [ ] Yetersiz stok davranışını tanımlamak; kritik eşikleri, iptal ve zayiat etkilerini test etmek.
- [ ] Tahmin simülasyonunu gerçek reçete ve stok kaynağıyla uyumlu hale getirmek; tahmini tüketimi gerçekleşen hareketlerden ayrı tutmak.

**Çıkış ölçütü:** Örnek ürün satışında beklenen hammadde hareketleri oluşur; tekrar istek ve iptal senaryoları stoğu yanlış değiştirmez.

## Aşama 4 — Erişim kontrolü ve operasyonel arayüzler

- [ ] Yerel ağda dahi çok cihazlı kullanıma açmadan önce personel kimlik doğrulaması, kasiyer/garson/mutfak/yönetici yetkileri ve CORS yapılandırması.
- [ ] Mobil garson PWA; masa başından sipariş alma ve açık hesabı görüntüleme.
- [ ] Canlı KDS ve masa güncellemeleri; WebSocket yeniden bağlandığında sunucudan durum eşitleme.
- [ ] Yönetici ekranında gerçekleşen satış, kritik stok ve tahmin kartları; tahmin ve yedek veri durumunun görünür olması.
- [ ] Parçalı ödeme, hesap bölme ve ürün varyasyonları; varyasyon fiyatı ve reçete etkisinin birlikte yönetilmesi.
- [ ] İşletmeye göre masa servisi / kasada peşin ödeme modelini seçebilme; self-servis için ödeme ve hazırlık yaşam döngülerini ayırma, ödeme sonrası hazırlık ve tekrar istek testleri.

**Çıkış ölçütü:** Yetkili farklı cihazlar aynı adisyon üzerinde tutarlı çalışır; rol dışı işlemler backend tarafından engellenir.

## Aşama 5 — Pilot hazırlığı ve saha doğrulaması

- [ ] PostgreSQL yedekleme ve geri yükleme denemesi; migration ve dağıtım prosedürü.
- [ ] Ödeme, iptal ve stok hareketlerinin izlenebilirliği; hata kayıtları ve günlük kasa mutabakatı.
- [ ] Ağ kesintisinde veri kaybını/çift işlemi önleyen davranış ve açık bağlantı durumu. Offline sipariş kuyruğu ayrıca tasarlanıp doğrulanmadan kullanılmaz.
- [ ] Kontrollü pilot kafede gerçek siparişlerle POS, KDS, stok ve ödeme doğrulaması.
- [ ] Gerçek veride tahmin ölçümü; eğitimde siparişsiz açık saatleri sıfır taleple tamamlama ve model iyileştirmeleri.

**Çıkış ölçütü:** Pilot satış ve stok kayıtları mutabık, yedekten dönüş denenmiş ve kritik hatalar giderilmiş olmalıdır.

## Pilot sonrasına bırakılan işler

- Tam offline-first sipariş senkronizasyonu ve çatışma çözümü.
- Zamanlanmış Telegram sabah/akşam raporları (mevcut bot gelen sorulara yanıt verir).
- E-Fatura / E-Arşiv ve ÖKC entegrasyonları; mevcut MVP'de harici cihazdaki tahsilat uygulamaya kaydedilir.
- İleri menü analitiği ve çok şube desteği.

## Sıradaki iş paketi

**Aşama 3:** tek kaynaklı reçete modeli → tüketim/iptal/zayiat politikası → izlenebilir stok hareketleri ve tekrar istek testleri. Arayüz kurulumu `../frontend/README.md`, backend sözleşmesi `ORDERS.md` dosyasındadır. Sonraki aşamaya ilgili çıkış ölçütü sağlandığında geçilir.
