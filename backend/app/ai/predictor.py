"""
CafeERP - Yapay Zeka Tahmin & Karar Destek Servisi (Inference & Decision Engine)
Eğitilmiş LightGBM modellerini (demand_forecast.pkl) kullanarak:
1. Belirtilen gün ve saat için talep & ciro tahmini üretir.
2. Gün boyu tahminleri reçetelerle birleştirerek hammaddelerin (çay, süt, ekmek, peynir)
   saat kaçta tükeneceğini (Burn-Rate) hesaplar ve proaktif aksiyon kartları döner.
"""

import joblib
import pandas as pd
import pickle
from threading import Lock
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent / "models" / "demand_forecast.pkl"

class ForecastUnavailableError(RuntimeError):
    """Eğitilmiş model kullanılamadığında tahmin yerine açık hata döndürür."""

class DemandPredictor:
    def __init__(self, model_path=None):
        self.model_path = Path(model_path) if model_path is not None else MODEL_PATH
        self.package = None
        self._load_lock = Lock()

    def _ensure_loaded(self):
        """Modeli ilk tahminde yükler; model eksikken satış API'si çalışmaya devam eder."""
        with self._load_lock:
            if self.package is not None:
                return
            try:
                package = joblib.load(self.model_path)
                models = package['models']
                feature_cols = package['feature_cols']
                if not feature_cols or any(
                    not callable(getattr(models[key], 'predict', None))
                    for key in ('traffic', 'tea', 'toast', 'hot_coffee', 'cold_drink', 'revenue')
                ):
                    raise ValueError('Geçersiz model paketi')
            except (OSError, ValueError, EOFError, ImportError, KeyError, TypeError, AttributeError, pickle.UnpicklingError) as exc:
                raise ForecastUnavailableError(
                    "Talep tahmin modeli kullanılamıyor. Modeli train_forecast.py ile yeniden eğitin."
                ) from exc
            self.models = models
            self.feature_cols = feature_cols
            self.package = package

    def predict_hour(self, hour: int, day_of_week: int, weather: str, temperature: int):
        """Tek bir saatlik dilim için tahmin üretir."""
        self._ensure_loaded()
        is_weekend = 1 if day_of_week in [5, 6] else 0
        is_wednesday = 1 if day_of_week == 2 else 0

        row = {
            'hour': hour,
            'day_of_week': day_of_week,
            'is_weekend': is_weekend,
            'is_wednesday': is_wednesday,
            'temperature': temperature,
            'weather_Bulutlu': 1 if weather == 'Bulutlu' else 0,
            'weather_Güneşli': 1 if weather == 'Güneşli' else 0,
            'weather_Rüzgarlı': 1 if weather == 'Rüzgarlı' else 0,
            'weather_Yağmurlu': 1 if weather == 'Yağmurlu' else 0,
        }
        df_in = pd.DataFrame([row])[self.feature_cols]

        # Tek satırlık çıkarımda çok iş parçacığı açma maliyetini önle.
        traffic = int(round(max(0, self.models['traffic'].predict(df_in, num_threads=1)[0])))
        tea = int(round(max(0, self.models['tea'].predict(df_in, num_threads=1)[0])))
        toast = int(round(max(0, self.models['toast'].predict(df_in, num_threads=1)[0])))
        hot_coffee = int(round(max(0, self.models['hot_coffee'].predict(df_in, num_threads=1)[0])))
        cold_drink = int(round(max(0, self.models['cold_drink'].predict(df_in, num_threads=1)[0])))
        revenue = round(float(max(0, self.models['revenue'].predict(df_in, num_threads=1)[0])), 2)

        return {
            "hour": hour,
            "predicted_traffic": traffic,
            "predicted_tea_glasses": tea,
            "predicted_toasts": toast,
            "predicted_hot_coffee": hot_coffee,
            "predicted_cold_drinks": cold_drink,
            "predicted_revenue": revenue
        }

    def simulate_day_burn_rate(self, day_of_week: int, weather: str, temperature: int, current_stocks: dict):
        """
        Günün 08:00 - 22:00 saatleri arasındaki tüketimi simüle eder.
        current_stocks örneği:
        {
            "rm_tea_leaf": 3000.0,   # gram
            "rm_milk_whole": 12000.0, # ml
            "rm_bread_toast": 80.0,   # dilim
            "rm_cheese_kasar": 2000.0 # gram
        }
        """
        hourly_forecasts = []
        burn_alerts = []

        stocks = current_stocks.copy()
        out_of_stock_tracker = {}

        for h in range(8, 23):
            pred = self.predict_hour(h, day_of_week, weather, temperature)
            hourly_forecasts.append(pred)

            # Reçete bazlı saatlik tüketim hesabı
            # 1 bardak çay = 3g çay yaprağı
            tea_leaf_needed = pred['predicted_tea_glasses'] * 3.0
            # Sıcak kahvelerin ortalama %70'i sütlü (Latte/Flat White): ~180 ml süt
            milk_needed = pred['predicted_hot_coffee'] * 0.70 * 180.0
            # 1 tost = 2 dilim ekmek, 55g kaşar
            bread_needed = pred['predicted_toasts'] * 2.0
            cheese_needed = pred['predicted_toasts'] * 55.0

            # Stok eksilt ve tükenme anını yakala
            materials = [
                ("rm_tea_leaf", "Çay Yaprağı (Dökme)", tea_leaf_needed, "gram"),
                ("rm_milk_whole", "Tam Yağlı Süt", milk_needed, "ml"),
                ("rm_bread_toast", "Tost Ekmeği", bread_needed, "dilim"),
                ("rm_cheese_kasar", "Kaşar Peyniri", cheese_needed, "gram"),
            ]

            for rm_id, name, needed, unit in materials:
                if rm_id in stocks:
                    stocks[rm_id] -= needed
                    if stocks[rm_id] <= 0 and rm_id not in out_of_stock_tracker:
                        out_of_stock_tracker[rm_id] = h
                        burn_alerts.append({
                            "material_id": rm_id,
                            "material_name": name,
                            "run_out_hour": f"{h:02d}:00",
                            "severity": "CRITICAL" if h <= 17 else "WARNING",
                            "message": f"[UYARI] {name} stogunuz yogunluk sebebiyle saat {h:02d}:00 civarinda tukenebilir! Lutfen erken tedarik saglayin."
                        })

        total_daily_revenue = sum(f['predicted_revenue'] for f in hourly_forecasts)
        total_daily_customers = sum(f['predicted_traffic'] for f in hourly_forecasts)

        # Vardiya tavsiyesi
        shift_recommendation = None
        peak_hour = max(hourly_forecasts, key=lambda x: x['predicted_traffic'])
        if peak_hour['predicted_traffic'] >= 25:
            shift_recommendation = {
                "peak_hour": f"{peak_hour['hour']:02d}:00",
                "traffic": peak_hour['predicted_traffic'],
                "message": f"[VARDIYA] Saat {peak_hour['hour']:02d}:00 piki icin tezgaha +1 personel/barista eklemeniz onerilir (Beklenen saatlik siparis: {peak_hour['predicted_traffic']})."
            }

        return {
            "summary": {
                "total_estimated_revenue": round(total_daily_revenue, 2),
                "total_estimated_customers": total_daily_customers,
                "weather": weather,
                "temperature": temperature
            },
            "alerts": burn_alerts,
            "shift_recommendation": shift_recommendation,
            "hourly_timeline": hourly_forecasts
        }

# Singleton instance
predictor = DemandPredictor()

if __name__ == "__main__":
    print("[*] Tahmin servisi test ediliyor...")
    test_stocks = {
        "rm_tea_leaf": 500.0,    # Sadece 500g çay var (çabuk biter)
        "rm_milk_whole": 4000.0,  # 4 Litre süt (öğleden sonra biter)
        "rm_bread_toast": 30.0,   # 30 dilim ekmek
        "rm_cheese_kasar": 1500.0
    }
    res = predictor.simulate_day_burn_rate(day_of_week=2, weather="Yağmurlu", temperature=14, current_stocks=test_stocks)
    print(f"\n[GÜNÜN ÖZETİ] Tahmini Ciro: {res['summary']['total_estimated_revenue']} TL | Müşteri: {res['summary']['total_estimated_customers']}")
    print("\n[PROAKTİF UYARI KARTLARI]:")
    for a in res['alerts']:
        print(f" -> {a['message']}")
    if res['shift_recommendation']:
        print(f" -> {res['shift_recommendation']['message']}")
