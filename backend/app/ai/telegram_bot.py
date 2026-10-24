"""
CafeERP - Telegram Akıllı Kafe Asistanı Botu (Telegram Bot Service)
Harici LLM gerektirmeden:
1. Telegram klavye butonları ile tek tıkla ciro, yoğunluk, stok ve brifing raporu sunar.
2. Kafe sahibinin yazdığı serbest Türkçe mesajları (NLU motoruyla) çözümler ve yanıtlar.
3. Token verilmediğinde veya '--sim' parametresiyle doğrudan terminal simülasyon modunda çalışabilir.
"""

import os
import sys
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# .env dosyasını otomatik yükle
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# Windows konsolunda emoji ve utf-8 karakter desteği
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from .decision_engine import decision_engine
except ImportError:
    from decision_engine import decision_engine

TELEGRAM_API_BASE = "https://api.telegram.org/bot"

# Telegram Menü Butonları (Persistent Reply Keyboard)
TELEGRAM_KEYBOARD = {
    "keyboard": [
        [{"text": "💰 Bugünkü Ciro & Satış"}, {"text": "👥 Kafe Yoğunluğu & Tahmin"}],
        [{"text": "🥛 Kritik Stok & Uyarılar"}, {"text": "📋 Günün Özeti & Brifing"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False
}

class CafeTelegramBot:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.engine = decision_engine
        self.offset = 0

    def send_message(self, chat_id: int, text: str, reply_markup: Optional[Dict] = None) -> bool:
        """Telegram API üzerinden kullanıcıya mesaj ve klavye gönderir."""
        if not self.token:
            return False
        
        url = f"{TELEGRAM_API_BASE}{self.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup or TELEGRAM_KEYBOARD
        }

        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                return True
            # Eğer Markdown ayrıştırma hatası olursa düz metin olarak tekrar dene
            payload.pop("parse_mode", None)
            res_plain = requests.post(url, json=payload, timeout=8)
            return res_plain.status_code == 200
        except Exception as e:
            print(f"[!] Mesaj gönderme hatası: {e}")
            return False

    def handle_message(self, text: str) -> str:
        """Kullanıcı mesajını işler ve cevap metnini döner."""
        # Buton metinlerini standartlaştır
        if "Ciro & Satış" in text:
            query = "bugün ne kadar satış yapıldı"
        elif "Kafe Yoğunluğu" in text:
            query = "bugün kafe yoğunluğu nedir"
        elif "Kritik Stok" in text:
            query = "kritik stok durumu"
        elif "Günün Özeti" in text:
            query = "günlük brifing özeti"
        else:
            query = text

        ans = self.engine.resolve_nl_query(query)
        return ans["text"]

    def run_polling(self):
        """Gerçek Telegram botunu dinleme (long-polling) döngüsü."""
        if not self.token:
            print("[HATA] TELEGRAM_BOT_TOKEN tanımlı değil! Lütfen token belirtin veya '--sim' ile çalıştırın.")
            return

        print(f"[*] CafeERP Telegram Botu başlatılıyor... (Token: {self.token[:8]}...)")
        print("[*] Telegram'dan gelen mesajlar dinleniyor. Çıkmak için Ctrl+C.")

        # Bot bilgisini kontrol et
        try:
            me_res = requests.get(f"{TELEGRAM_API_BASE}{self.token}/getMe", timeout=5).json()
            if me_res.get("ok"):
                bot_user = me_res["result"]["username"]
                print(f"[OK] Bot bağlandı: @{bot_user}")
            else:
                print(f"[!] Token geçersiz görünüyor: {me_res}")
                return
        except Exception as e:
            print(f"[!] Bağlantı hatası: {e}")
            return

        while True:
            try:
                url = f"{TELEGRAM_API_BASE}{self.token}/getUpdates?offset={self.offset}&timeout=20"
                res = requests.get(url, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    for update in data.get("result", []):
                        self.offset = update["update_id"] + 1
                        msg = update.get("message")
                        if not msg:
                            continue
                        
                        chat_id = msg["chat"]["id"]
                        text = msg.get("text", "")
                        user_name = msg["from"].get("first_name", "Kullanıcı")

                        print(f"[MESAJ] {user_name} ({chat_id}): {text}")
                        reply_text = self.handle_message(text)
                        self.send_message(chat_id, reply_text)
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n[*] Telegram botu durduruldu.")
                break
            except Exception as e:
                print(f"[!] Polling hatası: {e}")
                time.sleep(3)

    def run_simulation(self):
        """Terminal üzerinden Telegram etkileşimini simüle eder."""
        print("="*65)
        print("🤖 CafeERP TELEGRAM ASİSTANI - TERMİNAL SİMÜLASYONU")
        print("   (Harici LLM yok, doğrudan Veritabanı + LightGBM Motoru)")
        print("="*65)
        print("Hazır Butonlar:")
        print(" [1] 💰 Bugünkü Ciro & Satış")
        print(" [2] 👥 Kafe Yoğunluğu & Tahmin")
        print(" [3] 🥛 Kritik Stok & Uyarılar")
        print(" [4] 📋 Günün Özeti & Brifing")
        print("\nİpucu: Numara seçebilir veya 'bugün ne kadar satış yapıldı?' gibi")
        print("doğrudan Türkçe soru yazabilirsiniz. Çıkmak için 'q' yazın.")
        print("="*65 + "\n")

        button_map = {
            "1": "bugün ne kadar satış yapıldı",
            "2": "bugün kafe yoğunluğu nedir",
            "3": "kritik stok durumu",
            "4": "günlük brifing özeti"
        }

        while True:
            try:
                user_input = input("\n👤 Kafe Sahibi > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ['q', 'exit', 'cikis', 'quit']:
                    print("[*] Simülasyondan çıkıldı.")
                    break

                query = button_map.get(user_input, user_input)
                response = self.handle_message(query)

                print("\n🤖 Bot >")
                print(response)
                print("-" * 50)
            except KeyboardInterrupt:
                print("\n[*] Simülasyon sonlandırıldı.")
                break

if __name__ == "__main__":
    token = None
    if "--token" in sys.argv:
        try:
            token_idx = sys.argv.index("--token") + 1
            token = sys.argv[token_idx]
        except IndexError:
            pass

    bot = CafeTelegramBot(token=token)
    # Eğer komut satırında --sim varsa veya token yoksa simülasyona başla
    if "--sim" in sys.argv or not bot.token:
        bot.run_simulation()
    else:
        bot.run_polling()
