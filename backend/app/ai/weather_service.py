"""
CafeERP - Hava Durumu Servisi (Open-Meteo Entegrasyonu)
Ücretsiz, API anahtarı gerektirmeyen Open-Meteo servisi ile
kafenin konumuna göre anlık ve günlük hava durumu bilgisini çeker.
LightGBM modelinin beklediği formatta ('Güneşli', 'Bulutlu', 'Yağmurlu', 'Rüzgarlı') etiketler üretir.
"""

import requests
import os
import math
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv(Path(__file__).resolve().parents[3] / '.env')

# Varsayılan Konum: İstanbul / Kadıköy (Moda Kafe Bölgesi)
DEFAULT_LATITUDE = 40.99
DEFAULT_LONGITUDE = 29.03

def map_wmo_code_to_weather(wmo_code: int, windspeed: float) -> str:
    """
    WMO hava kodunu ve rüzgar hızını modelimizin kategorilerine eşler:
    - Rüzgarlı (Rüzgar > 28 km/s)
    - Yağmurlu (WMO 51-67, 80-82, 95-99)
    - Bulutlu (WMO 1-3, 45, 48)
    - Güneşli (WMO 0)
    """
    if windspeed >= 28.0:
        return "Rüzgarlı"

    # Yağmur, çisenti veya fırtına
    if (50 <= wmo_code <= 67) or (80 <= wmo_code <= 82) or (95 <= wmo_code <= 99):
        return "Yağmurlu"

    # Parçalı bulutlu, kapalı, sisli
    if wmo_code in [1, 2, 3, 45, 48]:
        return "Bulutlu"

    # Açık / Güneşli
    return "Güneşli"

def _coordinate(value, default, limit):
    """Eksik veya geçersiz konum ayarında varsayılan koordinatı kullanır."""
    try:
        result = float(value)
        return result if math.isfinite(result) and abs(result) <= limit else default
    except (TypeError, ValueError):
        return default

def get_current_weather(lat: float = None, lon: float = None) -> Dict[str, Any]:
    """
    Canlı hava durumunu döner. İnternet kesilirse veya API yanıt vermezse
    güvenli yedek (fallback) değerler döner.
    """
    lat = _coordinate(lat if lat is not None else os.getenv('CAFE_LATITUDE'), DEFAULT_LATITUDE, 90)
    lon = _coordinate(lon if lon is not None else os.getenv('CAFE_LONGITUDE'), DEFAULT_LONGITUDE, 180)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()["current_weather"]
            temp = round(float(data["temperature"]))
            wind = float(data["windspeed"])
            code = int(data["weathercode"])
            if not math.isfinite(wind):
                raise ValueError("Geçersiz rüzgar hızı")
            condition = map_wmo_code_to_weather(code, wind)
            return {
                "temperature": temp,
                "weather": condition,
                "windspeed": wind,
                "weather_code": code,
                "is_live": True,
                "description": f"{temp}°C, {condition}"
            }
    except Exception as e:
        # İnternet hatası olursa çökme, varsayılan değerle devam et
        pass

    return {
        "temperature": 18,
        "weather": "Güneşli",
        "windspeed": 12.0,
        "weather_code": 0,
        "is_live": False,
        "description": "18°C, Güneşli (Varsayılan)"
    }

if __name__ == "__main__":
    w = get_current_weather()
    print(f"[*] Canlı Hava Durumu Testi: {w}")
