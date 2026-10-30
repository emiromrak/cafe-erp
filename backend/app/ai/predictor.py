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

    def simulate_day_burn_rate(self, day_of_week: int, weather: str, temperature: int,
                               current_stocks: dict, recipe_mix=None, start_hour=8, start_minute=0):
        """SQL reçetelerinden, günün kalan saatleri için tahmini tüketim üretir.

        Gerçek stok veya hareket defteri değiştirilmez. Grup içindeki ürün
        dağılımı varsayımdır; reçetesi olmayan gruplar ayrıca raporlanır.
        """
        from decimal import Decimal
        hourly_forecasts, burn_alerts = [], []
        stocks = {key: Decimal(str(value)) for key, value in current_stocks.items()}
        depleted = set()
        for hour in range(max(8, start_hour), 23):
            pred = self.predict_hour(hour, day_of_week, weather, temperature)
            hourly_forecasts.append(pred)
            fraction = Decimal(60-start_minute)/60 if hour == start_hour else Decimal(1)
            needed = {}
            for key, lines in (recipe_mix or {}).items():
                for line in lines:
                    material_id = line['material_id']
                    quantity = Decimal(pred.get(key,0)) * line['quantity'] * fraction
                    if material_id not in needed:
                        needed[material_id] = [line, Decimal(0)]
                    needed[material_id][1] += quantity
            for material_id, (line, quantity) in needed.items():
                if material_id not in stocks or quantity <= 0:
                    continue
                stocks[material_id] -= quantity
                if stocks[material_id] <= 0 and material_id not in depleted:
                    depleted.add(material_id)
                    burn_alerts.append({
                        'material_id':material_id, 'material_name':line['name'],
                        'run_out_hour':f'{hour:02d}:00',
                        'severity':'CRITICAL' if hour <= 17 else 'WARNING',
                        'message':f"{line['name']} kalan gün içinde {hour:02d}:00 saat diliminde tükenebilir."
                    })
        peak = max(hourly_forecasts,key=lambda f:f['predicted_traffic'],default=None)
        shift = None
        if peak and peak['predicted_traffic'] >= 25:
            shift = {'peak_hour':f"{peak['hour']:02d}:00", 'traffic':peak['predicted_traffic'],
                     'message':'Yoğun saat için ek personel desteği planlayın.'}
        return {
            'summary': {
                'total_estimated_revenue':round(sum(f['predicted_revenue'] for f in hourly_forecasts),2),
                'total_estimated_customers':sum(f['predicted_traffic'] for f in hourly_forecasts),
                'weather':weather, 'temperature':temperature,
                'start_hour':start_hour, 'start_minute':start_minute,
                'recipe_groups':list(recipe_mix or {})
            },
            'alerts':burn_alerts, 'shift_recommendation':shift, 'hourly_timeline':hourly_forecasts
        }

# Uygulama genelinde paylaşılan tek örnek
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
