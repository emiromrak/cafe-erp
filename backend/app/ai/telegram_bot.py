"""
CafeERP - Telegram Akıllı Kafe Asistanı Botu (Telegram Bot Service)
1. Telegram klavye butonları ile tek tıkla ciro, yoğunluk, stok ve brifing raporu sunar.
2. Kafe sahibinin yazdığı serbest Türkçe mesajları (NLU motoruyla) çözümler ve yanıtlar.
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

# Mesajların kaydedileceği log dosyası
LOG_FILE = Path(os.getenv('CAFE_LOG_DIR', str(BASE_DIR))) / "telegram_messages.log"

# Windows konsolunda emoji ve utf-8 karakter desteği
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from .decision_engine import decision_engine
    from .predictor import ForecastUnavailableError
except ImportError:
    from decision_engine import decision_engine
    from predictor import ForecastUnavailableError

TELEGRAM_API_BASE = "https://api.telegram.org/bot"

# Telegram menü butonları (kalıcı yanıt klavyesi)
TELEGRAM_KEYBOARD = {
    "keyboard": [
        [{"text": "💰 Bugünkü Ciro & Satış"}, {"text": "👥 Kafe Yoğunluğu & Tahmin"}],
        [{"text": "🥛 Kritik Stok & Uyarılar"}, {"text": "📋 Günün Özeti & Brifing"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False
}

class CafeTelegramBot:
    def __init__(self, token: Optional[str] = None, allowed_user_ids=None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.engine = decision_engine
        self.offset = 0
        if allowed_user_ids is None:
            try:
                allowed_user_ids = {
                    int(value.strip()) for value in os.getenv('TELEGRAM_ALLOWED_USER_IDS', '').split(',')
                    if value.strip()
                }
            except ValueError:
                raise ValueError('TELEGRAM_ALLOWED_USER_IDS virgülle ayrılmış sayısal kullanıcı kimlikleri olmalı.') from None
        self.allowed_user_ids = set(allowed_user_ids)

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
            print(f"[!] Mesaj gönderme hatası: {type(e).__name__}")
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

        try:
            ans = self.engine.resolve_nl_query(query)
        except ForecastUnavailableError as exc:
            return str(exc)
        return ans["text"]

    def process_update(self, update):
        """Yalnızca izin verilen kullanıcının özel sohbetindeki metin mesajını işler."""
        msg = update.get('message', {})
        user_id = msg.get('from', {}).get('id')
        chat = msg.get('chat', {})
        text = msg.get('text')
        if user_id not in self.allowed_user_ids or chat.get('type') != 'private' or not isinstance(text, str):
            return False
        chat_id = chat['id']
        user_name = msg['from'].get('first_name', 'Kullanıcı')
        log_entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {user_name} ({chat_id}): {text}"
        print(f"[MESAJ] {log_entry}", flush=True)
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except OSError:
            pass
        return self.send_message(chat_id, self.handle_message(text))

    def run_polling(self):
        """Gerçek Telegram botunu dinleme (long-polling) döngüsü."""
        if not self.token:
            print("[HATA] TELEGRAM_BOT_TOKEN tanımlı değil!")
            return

        if not self.allowed_user_ids:
            print('[HATA] TELEGRAM_ALLOWED_USER_IDS tanımlı değil. Yetkili kullanıcı kimliklerini yapılandırın.')
            return

        print("[*] CafeERP Telegram Botu başlatılıyor...")
        print("[*] Telegram'dan gelen mesajlar dinleniyor. Çıkmak için Ctrl+C.")

        # Bot bilgisini kontrol et
        try:
            me_res = requests.get(f"{TELEGRAM_API_BASE}{self.token}/getMe", timeout=5).json()
            if me_res.get("ok"):
                bot_user = me_res["result"]["username"]
                print(f"[OK] Bot bağlandı: @{bot_user}")
            else:
                print("[!] Telegram bot kimliği doğrulanamadı.")
                return
        except Exception as e:
            print(f"[!] Bağlantı hatası: {type(e).__name__}")
            return

        while True:
            try:
                url = f"{TELEGRAM_API_BASE}{self.token}/getUpdates?offset={self.offset}&timeout=20"
                res = requests.get(url, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    for update in data.get("result", []):
                        self.offset = update["update_id"] + 1
                        self.process_update(update)
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n[*] Telegram botu durduruldu.")
                break
            except Exception as e:
                print(f"[!] Polling hatası: {type(e).__name__}")
                time.sleep(3)

if __name__ == "__main__":
    bot = CafeTelegramBot()
    bot.run_polling()
