# 📦 Modüller ve Operasyonel Akışlar

Bu dokümanda CafeERP'nin günlük kafe işleyişindeki temas noktaları ve kullanıcı akışları açıklanmıştır.

> **30 Ekim 2026 kapsam kararı:** Ürün iki işletme modelini de hedefler;
> ilk frontend masa servisi için geliştirilecektir. Bu belgedeki self-servis,
> varyasyon, parçalı ödeme, mobil PWA ve WebSocket açıklamaları hedef tasarımdır.
> Aşama 2; masa listesi, adisyon/menü, basit KDS ve servis sonrası tek seferde
> tam nakit/kart ödeme kaydı içerir. İşletmeye göre model seçimi ve kasada
> peşin ödeme akışı Aşama 4'te ele alınır. Güncel sıra `ROADMAP.md`, mevcut
> backend kuralları `ORDERS.md` dosyasındadır.

---

## 1. POS & Hızlı Satış Terminali (Kasa / Garson Arayüzü)

### Kullanım Senaryoları
1. **Self-Servis / Kasa Usulü (3. Nesil Kahve Dükkanı Akışı):**
   * Müşteri kasaya gelir.
   * Kasadaki personel kategori seçer (örn: Sıcak Kahveler -> Latte).
   * Açılan varyasyon modalından: *Boyut: Medium, Süt: Yulaf Sütü (+₺20)* seçer.
   * Ödeme alınır (Nakit / Kredi Kartı).
   * Tek tıkla sipariş "Hazırlanıyor" durumuna geçer ve mutfak ekranına (KDS) düşer.
2. **Masa Servisi Usulü (Bistro & Klasik Kafe Akışı):**
   * Garson salondaki krokiden boş masayı seçer (örn: Masa 4).
   * Siparişleri masaya ekler ve "Siparişi Onayla" der.
   * Siparişler mutfak ekranına düşerken masa "Dolu" durumuna geçer.
   * Müşteri kalkarken hesap parçalı (Alman usulü) veya tek parça kapatılır.
3. **Mobil Garson El Terminali (Masa Başında Anlık Sipariş ve Tahsilat):**
   * Garson kendi cep telefonundan PWA web arayüzünü açar.
   * Masanın başında dururken siparişleri (çay, tost, kahve vb.) akılda tutmaya gerek kalmadan telefondan işaretler.
   * "Siparişi Gönder"e bastığı anda WebSocket üzerinden:
     * Kasadaki masa adisyonuna siparişler anında eklenir.
     * Mutfak ve çay ocağı ekranına (KDS) sesli uyarıyla sipariş kartı düşer.
   * Garson masada hesap kapatmak isteyen müşterinin güncel adisyonunu telefonundan görüp tahsilatını onaylayabilir.

---

## 2. KDS (Kitchen Display System - Mutfak & Barista Ekranı)

* Masada veya kasada onaylanan her sipariş anında mutfaktaki dokunmatik tablete sesli/görsel uyarı ile düşer.
* Kart üzerinde: Sipariş saati, masa numarası/müşteri adı, ürünler ve özel notlar yer alır.
* Süre Sayacı:
  * 0 - 3 dakika: Yeşil
  * 4 - 6 dakika: Sarı
  * 7+ dakika: Kırmızı (Gecikme uyarısı)
* Barista siparişi tamamlayınca ekrana dokunarak "Hazır" durumuna getirir.

---

## 3. Reçete ve Dinamik Stok Düşüm Mantığı

Kafelerin en büyük maliyet kalemi olan hammadde firesini önler:
* Her bir sipariş tamamlandığında arka planda `recipes` tablosu tetiklenir.
* Örnek:
  * 1 Adet Latte satıldığında:
    * `Espresso Çekirdeği`: -18 gram
    * `Tam Yağlı Süt`: -220 ml
    * `Karton Bardak 12oz`: -1 adet
    * `Bardak Kapağı`: -1 adet
* Kritik seviyeye inen hammaddeler için anında AI uyarı mekanizması çalışır.

---

## 4. Yapay Zeka Katmanı: Çoklu Temas Noktası

Yapay zeka sadece bir chatbot ile sınırlı değildir. Kafe sahibinin gün içindeki yoğunluğuna uygun 3 kanaldan konuşur:

### A. Proaktif Dashboard Kartları (Push Notification)
Yönetim paneline girildiğinde en üstte beliren aksiyon kartları:
* ⚠️ **Stok Uyarısı:** *"Son 3 günün tüketim hızına göre Cuma 15:00'te Yulaf Sütü tükenecek. Tedarikçiyi aramalısın."*
* 👥 **Vardiya Önerisi:** *"Gelecek Çarşamba bölgede yağmur bekleniyor, geçmiş yağmurlu günlere göre %35 daha yoğun olacaksın. Akşam vardiyasına +1 barista ekle."*
* 💡 **Menü Mühendisliği:** *"San Sebastian Cheesecake kâr marjın %75 ancak menüde geride kalmış. Baristalara öneri yapmalarını söyleyin."*

### B. WhatsApp / Telegram Entegrasyonu (Cepteki Müdür)
Kafe sahibine günde 2 kez özet rapor iletir:
* **Sabah 09:00:** *"Günaydın! Bugün hava 22°C güneşli. Tahmini 85 soğuk kahve bekliyoruz. Buz ve süt stoğunuz yeterli."*
* **Gece 00:00:** *"Kapanış Özeti: 24.500 TL ciro yapıldı. En çok satan: Flat White (42 adet). Ortalama servis hızı: 4.2 dakika."*

### C. İnteraktif Sohbet (Chatbot)
Yönetim panelindeki sohbet asistanı sayesinde kafe sahibi konuşma diliyle işletmesini sorgular:
* *"Geçen aya göre kahve maliyetlerimiz ne kadar arttı?"*
* *"En çok hangi saatlerde masa boş kalıyor?"*
