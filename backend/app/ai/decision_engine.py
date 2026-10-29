"""
CafeERP - Kural Tabanlı Uzman Karar ve Öneri Motoru (LLM-less Expert Engine)
Harici LLM bağımlılığı olmadan:
1. SQLite veritabanındaki gerçek ciro, satış, masa ve stok kayıtlarını doğrudan sorgular.
2. LightGBM tahmin modeli (predictor.py) ve canlı hava durumunu (weather_service.py) harmanlar.
3. Kafe sahibinin serbestçe sorduğu Türkçe soruları (Niyet / Intent çözümleme ile) anında
   ve %100 matematiksel doğrulukla yanıtlar.
"""

import sqlite3
import re
import sys
from datetime import datetime
from contextlib import closing
from pathlib import Path
from typing import Dict, Any, List

# Windows konsolunda emoji ve utf-8 karakter desteği
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from .predictor import predictor
    from .weather_service import get_current_weather
except ImportError:
    from predictor import predictor
    from weather_service import get_current_weather

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = BASE_DIR / "data" / "sample_cafe.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH.resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def normalize_text(text: str) -> str:
    """Türkçe karakterleri ve küçük harfleri arama için standartlaştırır."""
    text = text.lower().strip()
    tr_map = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'i': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u'
    }
    for tr_char, eng_char in tr_map.items():
        text = text.replace(tr_char, eng_char)
    # Noktalama işaretlerini boşluğa çevir
    text = re.sub(r'[^\w\s]', ' ', text)
    return ' '.join(text.split())

class CafeDecisionEngine:
    def __init__(self):
        self.predictor = predictor

    def get_sales_summary(self, target_date: str = None) -> Dict[str, Any]:
        """
        Gerçekleşen satış ve ciro özetini veritabanından çeker.
        Eğer hedef tarih verilmezse ve bugüne ait sipariş yoksa, son aktif günün verilerini sunar.
        """
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()

            # En son tarihli günü öğren
            cursor.execute("SELECT MAX(substr(timestamp, 1, 10)) FROM orders")
            latest_db_date = cursor.fetchone()[0]

            today_str = datetime.now().strftime("%Y-%m-%d")
            query_date = target_date or today_str

            # Sorgulanan gün için sipariş sayısı
            cursor.execute("SELECT COUNT(*) FROM orders WHERE substr(timestamp, 1, 10) = ?", (query_date,))
            count = cursor.fetchone()[0]

            is_fallback = False
            display_date = query_date
            if count == 0 and target_date is None and latest_db_date is not None:
                # Bugün henüz sipariş girilmediyse son aktif güne dön
                query_date = latest_db_date
                display_date = latest_db_date
                is_fallback = True

            # Satış özetini al
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT order_id) as total_orders,
                    COALESCE(SUM(total_amount), 0) as total_revenue,
                    COALESCE(AVG(total_amount), 0) as avg_order_amount,
                    COALESCE(SUM(CASE WHEN payment_method = 'Kredi Kartı' THEN total_amount ELSE 0 END), 0) as card_revenue,
                    COALESCE(SUM(CASE WHEN payment_method = 'Nakit' THEN total_amount ELSE 0 END), 0) as cash_revenue
                FROM orders
                WHERE substr(timestamp, 1, 10) = ?
            """, (query_date,))
            stats = dict(cursor.fetchone())

            # En çok satan 5 ürünü al
            cursor.execute("""
                SELECT oi.product_name, SUM(oi.quantity) as total_qty, SUM(oi.quantity * oi.unit_price) as product_rev
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                WHERE substr(o.timestamp, 1, 10) = ?
                GROUP BY oi.product_name
                ORDER BY total_qty DESC
                LIMIT 5
            """, (query_date,))
            top_items = [dict(row) for row in cursor.fetchall()]

        # Mesaj metnini derle
        date_header = f"{display_date}"
        if is_fallback:
            intro = f"ℹ️ *Bugün ({today_str}) henüz sipariş kaydı girilmediğinden, son kapanan günün ({display_date}) verileri gösteriliyor:*\n"
        else:
            intro = f"📊 *{date_header} Tarihli Satış & Kasa Özeti:*\n"

        top_items_text = "\n".join([f"  • *{item['product_name']}:* {item['total_qty']} adet ({item['product_rev']:,.0f} TL)" for item in top_items]) or "  • Bu tarihte satış kaydı bulunmuyor."

        text = (
            f"{intro}\n"
            f"💰 *Toplam Ciro:* {stats['total_revenue']:,.2f} TL\n"
            f"🧾 *Toplam Sipariş / Fiş:* {stats['total_orders']} adet\n"
            f"🎯 *Ortalama Masa Sepeti:* {stats['avg_order_amount']:,.2f} TL\n"
            f"💳 *Kredi Kartı Tahsilatı:* {stats['card_revenue']:,.2f} TL\n"
            f"💵 *Nakit Tahsilat:* {stats['cash_revenue']:,.2f} TL\n\n"
            f"🏆 *Günün En Çok Satanları:*\n{top_items_text}"
        )

        return {
            "query_date": query_date,
            "is_fallback": is_fallback,
            "stats": stats,
            "top_items": top_items,
            "formatted_text": text
        }

    def get_traffic_and_forecast(self) -> Dict[str, Any]:
        """
        Canlı hava durumu ve LightGBM modelini kullanarak günün yoğunluk ve ciro tahminini döner.
        """
        now = datetime.now()
        day_of_week = now.weekday() # 0: Pazartesi ... 6: Pazar
        weather_info = get_current_weather()

        temp = weather_info["temperature"]
        weather = weather_info["weather"]

        # Günün saatlik tahminlerini üret
        hourly_forecasts = []
        for h in range(8, 23):
            pred = self.predictor.predict_hour(h, day_of_week, weather, temp)
            hourly_forecasts.append(pred)

        total_est_traffic = sum(f["predicted_traffic"] for f in hourly_forecasts)
        total_est_revenue = sum(f["predicted_revenue"] for f in hourly_forecasts)
        total_tea = sum(f["predicted_tea_glasses"] for f in hourly_forecasts)
        total_coffee = sum(f["predicted_hot_coffee"] for f in hourly_forecasts)
        total_toast = sum(f["predicted_toasts"] for f in hourly_forecasts)

        peak_hour = max(hourly_forecasts, key=lambda x: x["predicted_traffic"])

        # Vardiya tavsiyesi
        shift_note = ""
        if peak_hour["predicted_traffic"] >= 25:
            shift_note = f"⚠️ *Vardiya Uyarısı:* Saat *{peak_hour['hour']:02d}:00* piki için tezgaha +1 barista eklemeniz önerilir (Beklenen saatlik sipariş: {peak_hour['predicted_traffic']})."
        else:
            shift_note = "✅ *Vardiya Durumu:* Bugün standart kadro ile rahatça idare edilebilir."

        text = (
            f"👥 *Bugünkü Kafe Yoğunluk ve Talep Tahmini*\n\n"
            f"🌤️ *Hava Koşulları:* {weather_info['description']}\n"
            f"📈 *Tahmini Günlük Ciro:* ~{total_est_revenue:,.0f} TL\n"
            f"🚶 *Beklenen Toplam Masa/Müşteri:* ~{total_est_traffic} sipariş\n"
            f"🔥 *Günün En Yoğun Saati (Pik):* Saat *{peak_hour['hour']:02d}:00* ({peak_hour['predicted_traffic']} sipariş/saat)\n\n"
            f"☕ *Beklenen Ürün Hacmi:*\n"
            f"  • Bardak Çay: ~{total_tea} bardak\n"
            f"  • Sıcak Kahve (Latte vb.): ~{total_coffee} bardak\n"
            f"  • Tost Grubu: ~{total_toast} porsiyon\n\n"
            f"{shift_note}"
        )

        return {
            "weather": weather_info,
            "total_estimated_revenue": total_est_revenue,
            "total_estimated_traffic": total_est_traffic,
            "peak_hour": peak_hour,
            "hourly_timeline": hourly_forecasts,
            "formatted_text": text
        }

    def get_stock_and_burn_rate(self) -> Dict[str, Any]:
        """
        Mevcut hammadde stoklarını DB'den çeker, LightGBM erime hızını hesaplar
        ve erken tükenme alarmları üretir.
        """
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, category, unit, current_stock, min_alert FROM raw_materials")
            rows = [dict(r) for r in cursor.fetchall()]

        # Kritik eşiğin altına inmiş olanları bul
        low_stocks = [r for r in rows if r["current_stock"] <= r["min_alert"]]

        # Reçete simülasyonu için stok sözlüğü oluştur
        stock_dict = {r["id"]: float(r["current_stock"]) for r in rows}

        now = datetime.now()
        weather_info = get_current_weather()
        burn_sim = self.predictor.simulate_day_burn_rate(
            day_of_week=now.weekday(),
            weather=weather_info["weather"],
            temperature=weather_info["temperature"],
            current_stocks=stock_dict
        )

        burn_alerts = burn_sim["alerts"]

        # Metin hazırla
        text_lines = ["🥛 *Kritik Stok & Hammadde Erime Raporu*\n"]

        if burn_alerts:
            text_lines.append("🚨 *Yoğunluk Sebebiyle Bugün Tükenecekler (Erken Uyarı):*")
            for alert in burn_alerts:
                text_lines.append(f"  • *{alert['material_name']}* saat *{alert['run_out_hour']}* civarında tükenebilir! Erken tedarik önerilir.")
            text_lines.append("")

        if low_stocks:
            text_lines.append("⚠️ *Kritik Seviyenin Altındaki Hammaddeler (Depo Alarmı):*")
            for ls in low_stocks:
                text_lines.append(f"  • *{ls['name']}:* {ls['current_stock']:g} {ls['unit']} kaldı (Kritik Eşik: {ls['min_alert']:g} {ls['unit']})")
        else:
            text_lines.append("✅ Depoda kritik eşiğin altına düşen acil bir hammadde bulunmuyor.")

        text = "\n".join(text_lines)

        return {
            "low_stocks": low_stocks,
            "burn_alerts": burn_alerts,
            "formatted_text": text
        }

    def get_daily_brief(self) -> Dict[str, Any]:
        """Sabah kafe sahibine gönderilecek tam operasyonel brifing metni."""
        sales = self.get_sales_summary()
        traffic = self.get_traffic_and_forecast()
        stock = self.get_stock_and_burn_rate()

        text = (
            f"📋 *CafeERP Günlük Yönetici Brifingi*\n"
            f"📅 Tarih: {datetime.now().strftime('%d.%m.%Y')} | {traffic['weather']['description']}\n\n"
            f"🎯 *Günün Özeti & Hedefler:*\n"
            f"  • Beklenen Ciro: ~{traffic['total_estimated_revenue']:,.0f} TL\n"
            f"  • Beklenen Masa: ~{traffic['total_estimated_traffic']} müşteri\n"
            f"  • En Yoğun Zaman: Saat {traffic['peak_hour']['hour']:02d}:00\n\n"
            f"⚡ *Öne Çıkan Aksiyonlar:*\n"
        )

        if stock["burn_alerts"]:
            text += f"  • 🚨 {stock['burn_alerts'][0]['message']}\n"
        else:
            text += "  • ✅ Stok durumu gün boyu operasyon için yeterli görünüyor.\n"

        if traffic["peak_hour"]["predicted_traffic"] >= 25:
            text += f"  • 👥 Saat {traffic['peak_hour']['hour']:02d}:00 piki için tezgaha destek planlayın.\n"

        text += "\nİstediğiniz zaman aşağıdaki butonlardan anlık durumu sorgulayabilirsiniz."

        return {
            "sales": sales,
            "traffic": traffic,
            "stock": stock,
            "formatted_text": text
        }

    def resolve_nl_query(self, query: str) -> Dict[str, Any]:
        """
        Kullanıcının yazdığı serbest Türkçe soruyu (LLM'siz NLU kural motoruyla) çözümler:
        - 'bugün ne kadar satış yapıldı', 'ciro nedir', 'ne kadar kazandık' -> Satış
        - 'bugün kafe yoğunluğu nedir', 'kalabalık mı', 'yoğunlaşır' -> Yoğunluk
        - 'stok durumu', 'süt bitti mi', 'kritik malzeme' -> Stok
        - 'personel', 'vardiya', 'barista lazım mı' -> Vardiya
        - 'özet', 'rapor', 'durum nedir' -> Brifing
        """
        norm = normalize_text(query)

        # 1. SATIŞ / CİRO SORGUSU
        sales_keywords = ['satis', 'ciro', 'kazanc', 'hasılat', 'hasilat', 'kasa', 'para', 'ne kadar kazandik', 'adisyon', 'kac tl', 'ne sattik', 'fatura']
        if any(kw in norm for kw in sales_keywords) or ('ne kadar' in norm and 'satis' in norm):
            res = self.get_sales_summary()
            return {
                "intent": "SALES_SUMMARY",
                "title": "💰 Satış & Kasa Bilgisi",
                "text": res["formatted_text"],
                "quick_replies": ["👥 Yoğunluk Tahmini", "🥛 Stok Durumu", "📋 Günün Özeti"]
            }

        # 2. YOĞUNLUK / MÜŞTERİ TRAFİĞİ SORGUSU
        traffic_keywords = ['yogun', 'kalabalik', 'trafik', 'musteri', 'kac kisi', 'kac masa', 'doluluk', 'pik', 'doluluk']
        if any(kw in norm for kw in traffic_keywords):
            res = self.get_traffic_and_forecast()
            return {
                "intent": "TRAFFIC_FORECAST",
                "title": "👥 Kafe Yoğunluğu & Talep",
                "text": res["formatted_text"],
                "quick_replies": ["💰 Satış Durumu", "🥛 Stok Durumu", "📋 Günün Özeti"]
            }

        # 3. STOK / HAMMADDE / TÜKENME SORGUSU
        stock_keywords = ['stok', 'sut', 'cay', 'ekmek', 'peynir', 'kahve', 'tuken', 'hammadde', 'kritik', 'bitti mi', 'kalan', 'depo']
        if any(kw in norm for kw in stock_keywords):
            res = self.get_stock_and_burn_rate()
            return {
                "intent": "STOCK_STATUS",
                "title": "🥛 Stok & Hammadde Alarmı",
                "text": res["formatted_text"],
                "quick_replies": ["💰 Satış Durumu", "👥 Yoğunluk Tahmini", "📋 Günün Özeti"]
            }

        # 4. VARDİYA / PERSONEL SORGUSU
        shift_keywords = ['vardiya', 'personel', 'barista', 'calisan', 'eleman', 'kac kisi lazim']
        if any(kw in norm for kw in shift_keywords):
            traffic = self.get_traffic_and_forecast()
            peak = traffic["peak_hour"]
            text = (
                f"👥 *Vardiya ve Personel Planlama Tavsiyesi*\n\n"
                f"• Günün En Yoğun Saati: *{peak['hour']:02d}:00*\n"
                f"• Beklenen Sipariş Hacmi: *{peak['predicted_traffic']} sipariş/saat*\n\n"
            )
            if peak["predicted_traffic"] >= 25:
                text += f"⚡ *Öneri:* Saat {peak['hour']-1:02d}:30 ile {peak['hour']+1:02d}:30 arasında tezgaha en az +1 barista / personel desteği sağlanmalıdır."
            else:
                text += "✅ *Öneri:* Bugünkü yoğunluk seviyesi tek ana barista ile rahatlıkla yürütülebilir seviyededir."

            return {
                "intent": "SHIFT_ADVICE",
                "title": "👥 Vardiya Planlama Tavsiyesi",
                "text": text,
                "quick_replies": ["💰 Satış Durumu", "👥 Yoğunluk Tahmini", "📋 Günün Özeti"]
            }

        # 5. GÜNLÜK ÖZET / RAPOR / BRİFİNG
        brief_keywords = ['ozet', 'rapor', 'durum', 'brifing', 'tavsiye', 'ne yapmaliyim', 'gunluk']
        if any(kw in norm for kw in brief_keywords):
            res = self.get_daily_brief()
            return {
                "intent": "DAILY_BRIEF",
                "title": "📋 Günlük Yönetici Brifingi",
                "text": res["formatted_text"],
                "quick_replies": ["💰 Bugünkü Ciro", "👥 Yoğunluk Tahmini", "🥛 Stok Durumu"]
            }

        # 6. SELAMLAMA / YARDIM
        greeting_keywords = ['merhaba', 'selam', 'gunaydin', 'iyi aksamlar', 'hey', 'start', 'yardim', 'help', 'komut']
        if any(kw in norm for kw in greeting_keywords) or len(norm) <= 3:
            text = (
                "☕ *CafeERP Akıllı Kafe Asistanına Hoş Geldiniz!*\n\n"
                "Ben kafenizin satışlarını, anlık stoklarını ve makine öğrenmesi yoğunluk tahminlerini takip eden operasyon danışmanınızım.\n\n"
                "Bana şunları sorabilirsiniz:\n"
                "• *'Bugün ne kadar satış yapıldı?'* veya *'Ciro kaç?'*\n"
                "• *'Bugün kafe yoğunluğu nedir?'* veya *'Pik saati ne zaman?'*\n"
                "• *'Kritik stok var mı?'* veya *'Süt ne zaman biter?'*\n"
                "• *'Günün genel durumu nedir?'*\n\n"
                "Ya da aşağıdaki hızlı butonlara dokunabilirsiniz 👇"
            )
            return {
                "intent": "GREETING",
                "title": "☕ CafeERP Asistanı",
                "text": text,
                "quick_replies": ["💰 Bugünkü Ciro & Satış", "👥 Kafe Yoğunluğu & Tahmin", "🥛 Kritik Stok & Uyarılar", "📋 Günün Özeti"]
            }

        # 7. EŞLEŞMEYEN SORULAR İÇİN AKILLI YÖNLENDİRME (YEDEK YANIT)
        text = (
            f"🤔 *'{query}'* sorunuzu tam olarak anlayamadım.\n\n"
            "Kafenizle ilgili en doğru bilgiyi alabilmek için şu konulardan birini sorabilir veya aşağıdaki butonları kullanabilirsiniz:\n"
            "• 💰 *Ciro & Satış:* 'Bugünkü ciro nedir?'\n"
            "• 👥 *Yoğunluk:* 'Bugün kafe yoğunluğu nedir?'\n"
            "• 🥛 *Stok:* 'Hammadde stokları ne durumda?'\n"
            "• 📋 *Günün Özeti:* 'Bana genel durumu anlat.'"
        )
        return {
            "intent": "UNKNOWN",
            "title": "❓ Nasıl Yardımcı Olabilirim?",
            "text": text,
            "quick_replies": ["💰 Bugünkü Ciro & Satış", "👥 Kafe Yoğunluğu & Tahmin", "🥛 Kritik Stok & Uyarılar", "📋 Günün Özeti"]
        }

# Uygulama genelinde paylaşılan tek örnek
decision_engine = CafeDecisionEngine()

if __name__ == "__main__":
    print("="*60)
    print("[TEST 1] Kullanıcı Sorusu: 'bugün ne kadar satış yapıldı?'")
    print("="*60)
    ans1 = decision_engine.resolve_nl_query("bugün ne kadar satış yapıldı?")
    print(ans1["text"])

    print("\n" + "="*60)
    print("[TEST 2] Kullanıcı Sorusu: 'bugün kafe yoğunluğu nedir?'")
    print("="*60)
    ans2 = decision_engine.resolve_nl_query("bugün kafe yoğunluğu nedir?")
    print(ans2["text"])
