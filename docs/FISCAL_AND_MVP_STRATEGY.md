# 🧾 Mali Fiş, ÖKC ve MVP Stratejisi

Bu dokümanda Türkiye'deki yasal yazarkasa/mali mevzuat dinamikleri ve CafeERP'nin MVP (Minimum Viable Product) aşamasında izleyeceği strateji açıklanmıştır.

---

## 1. Temel Kavramlar

### A. MVP (Minimum Viable Product - Minimum Uygulanabilir Ürün)
Bir ürün fikrinin pazara çıkabilecek ve kullanıcılara değer katabilecek en temel, çalışan ilk sürümüdür.
* Fazla özellik ekleyerek aylarca kod yazıp gecikmek yerine, çekirdek değer önerisini (Sipariş + Stok + AI Tahmin) sahada test etmeyi sağlar.

### B. Mali Fiş (ÖKC - Ödeme Kaydedici Cihaz)
Türkiye'de Gelir İdaresi Başkanlığı (GİB) mevzuatına göre restoran ve kafelerin satılan her ürün için devlete onaylı bir cihazdan (Beko, Ingenico, Hugin vb.) mali fiş kesmesi zorunludur. Bu cihazlar gün sonu "Z Raporu" basarak devlete vergi bildirir.

### C. Mali Entegrasyon
Tablet/web uygulamasının bu resmi yazarkasa cihazıyla (kablo, Wi-Fi veya Bluetooth üzerinden) konuşarak tutarı otomatik cihaza göndermesi ve fişi bastırması işlemidir.

---

## 2. Neden İlk Aşamada (MVP) Mali Entegrasyon Yapmıyoruz?

1. **Yüksek Lisans ve Sertifikasyon Maliyetleri:**
   * ÖKC donanım üreticileri (Beko, Ingenico vb.) bağımsız yazılımcılardan entegrasyon protokolleri ve test ortamları için yüksek ücretler ve resmi taahhütler talep eder.
   * GİB onay süreçleri aylar sürebilir.
2. **Bağımsız Kafelerin Mevcut Çalışma Alışkanlığı:**
   * Türkiye'deki butik kafelerin %80'i sipariş takibini, adisyonu ve mutfağı tablet üzerindeki yazılımdan yürütür.
   * Ödeme anında müşteri kartını uzattığında, personel tutarı mevcut banka yazarkasa pos cihazına eliyle tuşlar (örn: 120 TL yazar, kartı çeker, müşteriye mali fişi verir) ve tablette "Ödendi"ye basar.
   * Bu yöntem yasalara uygundur ve kafe için sorunsuz çalışır.

---

## 3. Yol Haritamızdaki Mali Plan (Fazlar)

* **Faz 1 (MVP - Mevcut Durum):**
  * Bağımsız ve donanımdan bağımsız bulut ERP.
  * İç adisyon, mutfak ekranı, reçete stok takibi ve yapay zeka operasyon danışmanı.
  * Mali fiş kesimi personelin mevcut yazarkasasından elle tuşlaması ile gerçekleşir.

* **Faz 2 (Ölçeklenme & Büyüme):**
  * E-Arşiv / E-Fatura entegratörleri (Paraşüt, KolayBi, Foriba vb.) ile doğrudan entegrasyon.
  * Yaygın ÖKC üreticileri (Beko / Hugin) ile resmi protokol entegrasyonu.
