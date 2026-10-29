"""
CafeERP - Makine Öğrenmesi Talep ve Yoğunluk Tahmin Modeli Eğitimi
(LightGBM Demand & Traffic Forecaster)

Bu script:
1. sample_cafe.db veritabanındaki 37.000+ siparişi saatlik bazda gruplar.
2. Saat, gün, hafta sonu, Çarşamba yoğunluğu, hava durumu ve sıcaklık özniteliklerini (features) çıkarır.
3. LightGBM regresyon modeli ile:
   - Saatlik Müşteri / Sipariş Yoğunluğu (Traffic)
   - Saatlik Çay Talebi (Bardak Çay)
   - Saatlik Tost Talebi (Kaşarlı & Karışık Tost)
   - Saatlik Sıcak Kahve (Latte / Flat White)
   - Saatlik Soğuk İçecek (Cold Brew / Iced Latte / Soda)
   tahmin modellerini eğitir.
4. Test seti (son 30 gün) üzerinde MAE, RMSE ve R2 başarı metriklerini raporlar.
5. Modeli 'backend/app/ai/models/demand_forecast.pkl' olarak kaydeder.
"""

import sqlite3
import sys
from contextlib import closing
from tempfile import NamedTemporaryFile
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = BASE_DIR / "data" / "sample_cafe.db"
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_FILE = MODEL_DIR / "demand_forecast.pkl"

def load_and_preprocess_data(db_path=None):
    """Kalemleri önce adisyon bazında toplar; her adisyonun cirosunu yalnızca bir kez sayar."""
    db_path = Path(db_path) if db_path is not None else DB_PATH
    print(f"[*] Veritabanı okunuyor: {db_path}")

    # 1. Saatlik özet veriyi çıkar
    query = """
    WITH item_totals AS (
        SELECT order_id,
            SUM(CASE WHEN product_id = 'prod_tea_glass' THEN quantity ELSE 0 END) AS tea_qty,
            SUM(CASE WHEN product_id IN ('prod_toast_cheese', 'prod_toast_mixed') THEN quantity ELSE 0 END) AS toast_qty,
            SUM(CASE WHEN product_id IN ('prod_latte', 'prod_flat_white', 'prod_americano', 'prod_filter', 'prod_turkish_coffee') THEN quantity ELSE 0 END) AS hot_coffee_qty,
            SUM(CASE WHEN product_id IN ('prod_cold_brew', 'prod_iced_latte', 'prod_soda', 'prod_ayran') THEN quantity ELSE 0 END) AS cold_drink_qty
        FROM order_items
        GROUP BY order_id
    )
    SELECT
        substr(o.timestamp, 1, 10) as order_date,
        CAST(substr(o.timestamp, 12, 2) AS INTEGER) as hour,
        o.weekday,
        o.weather,
        o.temperature,
        COUNT(DISTINCT o.order_id) as order_count,
        SUM(o.total_amount) as total_revenue,
        COALESCE(SUM(oi.tea_qty), 0) as tea_qty,
        COALESCE(SUM(oi.toast_qty), 0) as toast_qty,
        COALESCE(SUM(oi.hot_coffee_qty), 0) as hot_coffee_qty,
        COALESCE(SUM(oi.cold_drink_qty), 0) as cold_drink_qty
    FROM orders o
    LEFT JOIN item_totals oi ON o.order_id = oi.order_id
    GROUP BY order_date, hour, o.weekday, o.weather, o.temperature
    ORDER BY order_date, hour
    """
    with closing(sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)) as conn:
        df = pd.read_sql_query(query, conn)
    if df.empty:
        raise ValueError("Model eğitimi için sipariş verisi bulunamadı.")

    print(f"[OK] Toplam {len(df)} saatlik zaman dilimi kaydı yüklendi.")

    # 2. Özellik Mühendisliği (Feature Engineering)
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['day_of_week'] = df['order_date'].dt.day_of_week # 0: Pazartesi, 6: Pazar
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['is_wednesday'] = (df['day_of_week'] == 2).astype(int)

    # Hava durumu kategorilerini sayısala dönüştür (One-Hot Encoding)
    weather_dummies = pd.get_dummies(df['weather'], prefix='weather', drop_first=False).astype(int)
    df = pd.concat([df, weather_dummies], axis=1)

    return df

def train_models():
    """Son 30 günü ayırarak modelleri eğitir ve başarılı paketi atomik olarak kaydeder."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df = load_and_preprocess_data()

    # Model girdileri (X)
    feature_cols = [
        'hour', 'day_of_week', 'is_weekend', 'is_wednesday', 'temperature',
        'weather_Bulutlu', 'weather_Güneşli', 'weather_Rüzgarlı', 'weather_Yağmurlu'
    ]

    # Eksik hava sütunu varsa 0 ile doldur
    for col in ['weather_Bulutlu', 'weather_Güneşli', 'weather_Rüzgarlı', 'weather_Yağmurlu']:
        if col not in df.columns:
            df[col] = 0

    # Kronolojik Zaman Bölümlemesi (Time-based Train/Test Split)
    # Son 30 günü test için ayıralım
    split_date = df['order_date'].max() - pd.Timedelta(days=30)
    train_mask = df['order_date'] <= split_date
    test_mask = df['order_date'] > split_date
    if not train_mask.any() or test_mask.sum() < 2:
        raise ValueError("Eğitim için 30 günden uzun geçmiş ve en az iki test zaman dilimi gerekir.")

    X_train = df.loc[train_mask, feature_cols]
    X_test = df.loc[test_mask, feature_cols]

    targets = {
        'traffic': 'order_count',
        'tea': 'tea_qty',
        'toast': 'toast_qty',
        'hot_coffee': 'hot_coffee_qty',
        'cold_drink': 'cold_drink_qty',
        'revenue': 'total_revenue'
    }

    trained_models = {}
    metrics = {}

    print("\n" + "="*60)
    print("[AI] LIGHTGBM MODELLERI EGITILIYOR (Zaman Serisi Regresyonu)")
    print("="*60)

    for key, target_col in targets.items():
        y_train = df.loc[train_mask, target_col]
        y_test = df.loc[test_mask, target_col]

        model = LGBMRegressor(
            n_estimators=120,
            learning_rate=0.06,
            max_depth=5,
            num_leaves=24,
            random_state=42,
            verbosity=-1
        )
        model.fit(X_train, y_train)

        # Tahmin ve değerlendirme
        y_pred = model.predict(X_test)
        y_pred = np.clip(y_pred, 0, None) # Negatif tahmin olamaz

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        trained_models[key] = model
        metrics[key] = {'MAE': round(mae, 2), 'RMSE': round(rmse, 2), 'R2': round(r2, 3)}

        print(f"[OK] {key.upper().ljust(12)} -> MAE: {mae:5.2f} | RMSE: {rmse:5.2f} | R2 Skoru: {r2:5.3f}")

    # Paketi diske kaydet
    package = {
        'models': trained_models,
        'feature_cols': feature_cols,
        'metrics': metrics,
        'trained_at': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    package['data_summary'] = {
        'hourly_rows': len(df),
        'total_orders': int(df['order_count'].sum()),
        'total_revenue': round(float(df['total_revenue'].sum()), 2),
        'revenue_aggregation': 'once_per_order',
        'train_end': split_date.strftime('%Y-%m-%d'),
    }
    with NamedTemporaryFile(dir=MODEL_DIR, suffix='.pkl', delete=False) as temp:
        temporary_path = Path(temp.name)
    try:
        joblib.dump(package, temporary_path)
        temporary_path.replace(MODEL_FILE)
    finally:
        temporary_path.unlink(missing_ok=True)
    print(f"\n[OK] Model paketi basariyla kaydedildi: {MODEL_FILE}")

    # 4. Örnek Bir Gelecek Tahmini Simülasyonu
    print("\n" + "="*60)
    print("[TEST] ORNEK GELECEK TAHMINI (Yarin Carsamba 16:00 | 14C Yagmurlu)")
    print("="*60)

    sample_input = pd.DataFrame([{
        'hour': 16,
        'day_of_week': 2, # Çarşamba
        'is_weekend': 0,
        'is_wednesday': 1,
        'temperature': 14,
        'weather_Bulutlu': 0,
        'weather_Güneşli': 0,
        'weather_Rüzgarlı': 0,
        'weather_Yağmurlu': 1
    }])[feature_cols]

    sim_traffic = int(round(trained_models['traffic'].predict(sample_input)[0]))
    sim_tea = int(round(trained_models['tea'].predict(sample_input)[0]))
    sim_toast = int(round(trained_models['toast'].predict(sample_input)[0]))
    sim_hot = int(round(trained_models['hot_coffee'].predict(sample_input)[0]))
    sim_cold = int(round(trained_models['cold_drink'].predict(sample_input)[0]))
    sim_rev = round(trained_models['revenue'].predict(sample_input)[0], 2)

    print(f"Beklenen Saatlik Siparis  : {sim_traffic} masa/musteri")
    print(f"Beklenen Bardak Cay       : {sim_tea} bardak")
    print(f"Beklenen Tost             : {sim_toast} porsiyon")
    print(f"Beklenen Sicak Kahve      : {sim_hot} bardak")
    print(f"Beklenen Soguk Icecek     : {sim_cold} adet")
    print(f"Beklenen Saatlik Ciro     : {sim_rev} TL")
    print("="*60)

if __name__ == "__main__":
    train_models()
