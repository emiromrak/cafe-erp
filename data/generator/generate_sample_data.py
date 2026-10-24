"""
CafeERP - Kapsamlı Gerçekçi Örnek Veri Üreteci (Sample Data Generator)
Hem modern 3. nesil kahve hem de geleneksel çay, tost ve masa/okey dinamiklerini içerir:
- Hammaddeler ve Depo Stokları (Çay yaprağı, şeker, peynir, ekmek, kahve, süt)
- Menü Kategorileri, Ürünler ve Fiyatlar
- Reçeteler (Ürün -> Hammadde eşleştirmesi / BOM)
- Salon Masaları (Masa 1-6, Bahçe 1-4, Okey 1-4, Paket)
- Personel ve Hızlı Giriş PIN Kodları (Garson, Kasiyer, Barista/Çaycı, Yönetici)
- 6 Aylık Gerçekçi Sipariş Geçmişi (Hava durumu, gün içi pikler, seri çay siparişleri)
"""

import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent
OUTPUT_JSON = DATA_DIR / "sample_cafe_data.json"
OUTPUT_DB = DATA_DIR / "sample_cafe.db"

# 1. HAMMADDELER (Depo Stokları)
RAW_MATERIALS = [
    # Çay & Geleneksel
    {"id": "rm_tea_leaf", "name": "Rize Çay Yaprağı (Dökme)", "category": "Çay", "unit": "gram", "current_stock": 40000.0, "min_alert": 8000.0, "cost": 0.25},
    {"id": "rm_sugar_cube", "name": "Küp Şeker (Tekli Sargılı)", "category": "Sarf", "unit": "adet", "current_stock": 5000.0, "min_alert": 1000.0, "cost": 0.30},
    {"id": "rm_turkish_coffee_grind", "name": "Türk Kahvesi (Taze Çekim)", "category": "Kahve", "unit": "gram", "current_stock": 8000.0, "min_alert": 2000.0, "cost": 0.50},

    # Kahveler & Süt
    {"id": "rm_coffee_blend", "name": "Espresso Blend Çekirdek", "category": "Kahve", "unit": "gram", "current_stock": 25000.0, "min_alert": 5000.0, "cost": 0.45},
    {"id": "rm_coffee_ethiopia", "name": "Etiyopya Tek Köken Çekirdek", "category": "Kahve", "unit": "gram", "current_stock": 10000.0, "min_alert": 2000.0, "cost": 0.65},
    {"id": "rm_milk_whole", "name": "Tam Yağlı Süt", "category": "Süt", "unit": "ml", "current_stock": 60000.0, "min_alert": 15000.0, "cost": 0.035},
    {"id": "rm_milk_oat", "name": "Yulaf Sütü (Barista Edition)", "category": "Süt", "unit": "ml", "current_stock": 18000.0, "min_alert": 5000.0, "cost": 0.085},

    # Tost & Mutfak Malzemeleri
    {"id": "rm_bread_toast", "name": "Tost Ekmeği (Dilimli)", "category": "Mutfak", "unit": "dilim", "current_stock": 400.0, "min_alert": 80.0, "cost": 3.50},
    {"id": "rm_cheese_kasar", "name": "Taze Kaşar Peyniri", "category": "Mutfak", "unit": "gram", "current_stock": 12000.0, "min_alert": 2500.0, "cost": 0.40},
    {"id": "rm_sucuk", "name": "Kasap Sucuk", "category": "Mutfak", "unit": "gram", "current_stock": 6000.0, "min_alert": 1500.0, "cost": 0.85},
    {"id": "rm_butter", "name": "Köy Tereyağı", "category": "Mutfak", "unit": "gram", "current_stock": 4000.0, "min_alert": 1000.0, "cost": 0.55},

    # Meşrubatlar & Hazır Ürünler
    {"id": "rm_bottle_soda", "name": "Şişe Maden Suyu (200ml)", "category": "İçecek", "unit": "adet", "current_stock": 480.0, "min_alert": 100.0, "cost": 12.0},
    {"id": "rm_bottle_ayran", "name": "Kutu Ayran (300ml)", "category": "İçecek", "unit": "adet", "current_stock": 240.0, "min_alert": 60.0, "cost": 14.0},
    {"id": "rm_cake_san_sebastian", "name": "San Sebastian Dilimi", "category": "Tatlı", "unit": "dilim", "current_stock": 24.0, "min_alert": 6.0, "cost": 65.0},
    {"id": "rm_croissant", "name": "Tereyağlı Kruvasan", "category": "Pastane", "unit": "adet", "current_stock": 30.0, "min_alert": 8.0, "cost": 35.0},

    # Ambalaj
    {"id": "rm_cup_12oz", "name": "Karton Bardak 12oz", "category": "Ambalaj", "unit": "adet", "current_stock": 1000.0, "min_alert": 250.0, "cost": 2.20},
    {"id": "rm_lid_12oz", "name": "Bardak Kapağı 12oz", "category": "Ambalaj", "unit": "adet", "current_stock": 1000.0, "min_alert": 250.0, "cost": 0.80},
]

# 2. KATEGORİLER
CATEGORIES = [
    {"id": "cat_traditional", "name": "Geleneksel & Çaylar", "display_order": 1},
    {"id": "cat_hot_coffee", "name": "Sıcak Kahveler", "display_order": 2},
    {"id": "cat_cold_drinks", "name": "Soğuk İçecekler & Meşrubat", "display_order": 3},
    {"id": "cat_food_kitchen", "name": "Tost & Atıştırmalıklar", "display_order": 4},
    {"id": "cat_bakery", "name": "Fırın & Tatlılar", "display_order": 5},
]

# 3. ÜRÜNLER
PRODUCTS = [
    # Geleneksel
    {"id": "prod_tea_glass", "cat_id": "cat_traditional", "name": "Bardak Çay", "price": 25.0, "type": "tea"},
    {"id": "prod_tea_pot", "cat_id": "cat_traditional", "name": "Demlik Çay (Semaver/Masa)", "price": 90.0, "type": "tea"},
    {"id": "prod_turkish_coffee", "cat_id": "cat_traditional", "name": "Türk Kahvesi", "price": 60.0, "type": "hot"},

    # Sıcak Kahveler
    {"id": "prod_latte", "cat_id": "cat_hot_coffee", "name": "Caffe Latte", "price": 120.0, "type": "hot"},
    {"id": "prod_flat_white", "cat_id": "cat_hot_coffee", "name": "Flat White", "price": 130.0, "type": "hot"},
    {"id": "prod_americano", "cat_id": "cat_hot_coffee", "name": "Americano", "price": 100.0, "type": "hot"},
    {"id": "prod_filter", "cat_id": "cat_hot_coffee", "name": "Filtre Kahve", "price": 90.0, "type": "hot"},

    # Soğuk İçecekler
    {"id": "prod_iced_latte", "cat_id": "cat_cold_drinks", "name": "Iced Latte", "price": 135.0, "type": "cold"},
    {"id": "prod_cold_brew", "cat_id": "cat_cold_drinks", "name": "Cold Brew", "price": 140.0, "type": "cold"},
    {"id": "prod_soda", "cat_id": "cat_cold_drinks", "name": "Maden Suyu (Soda)", "price": 30.0, "type": "cold"},
    {"id": "prod_ayran", "cat_id": "cat_cold_drinks", "name": "Yayık Ayran", "price": 35.0, "type": "cold"},

    # Tost & Mutfak
    {"id": "prod_toast_cheese", "cat_id": "cat_food_kitchen", "name": "Kaşarlı Tost", "price": 80.0, "type": "food"},
    {"id": "prod_toast_mixed", "cat_id": "cat_food_kitchen", "name": "Karışık Tost (Sucuk & Kaşar)", "price": 100.0, "type": "food"},

    # Fırın & Tatlı
    {"id": "prod_san_sebastian", "cat_id": "cat_bakery", "name": "San Sebastian Cheesecake", "price": 195.0, "type": "food"},
    {"id": "prod_croissant", "cat_id": "cat_bakery", "name": "Tereyağlı Kruvasan", "price": 110.0, "type": "food"},
]

# 4. REÇETELER (BOM - Her Satışta Depodan Düşen Hammaddeler)
RECIPES = {
    "prod_tea_glass": [
        {"rm_id": "rm_tea_leaf", "qty": 3.0},       # 3 gram çay
        {"rm_id": "rm_sugar_cube", "qty": 2.0},     # 2 adet şeker
    ],
    "prod_tea_pot": [
        {"rm_id": "rm_tea_leaf", "qty": 25.0},      # 25 gram dökme çay
        {"rm_id": "rm_sugar_cube", "qty": 8.0},     # 8 adet şeker
    ],
    "prod_turkish_coffee": [
        {"rm_id": "rm_turkish_coffee_grind", "qty": 9.0}, # 9 gram kahve
        {"rm_id": "rm_sugar_cube", "qty": 1.0},
    ],
    "prod_latte": [
        {"rm_id": "rm_coffee_blend", "qty": 18.0},
        {"rm_id": "rm_milk_whole", "qty": 220.0},
        {"rm_id": "rm_cup_12oz", "qty": 1.0},
        {"rm_id": "rm_lid_12oz", "qty": 1.0},
    ],
    "prod_flat_white": [
        {"rm_id": "rm_coffee_blend", "qty": 20.0},
        {"rm_id": "rm_milk_whole", "qty": 150.0},
        {"rm_id": "rm_cup_12oz", "qty": 1.0},
        {"rm_id": "rm_lid_12oz", "qty": 1.0},
    ],
    "prod_americano": [
        {"rm_id": "rm_coffee_blend", "qty": 18.0},
        {"rm_id": "rm_cup_12oz", "qty": 1.0},
        {"rm_id": "rm_lid_12oz", "qty": 1.0},
    ],
    "prod_filter": [
        {"rm_id": "rm_coffee_ethiopia", "qty": 15.0},
        {"rm_id": "rm_cup_12oz", "qty": 1.0},
        {"rm_id": "rm_lid_12oz", "qty": 1.0},
    ],
    "prod_iced_latte": [
        {"rm_id": "rm_coffee_blend", "qty": 18.0},
        {"rm_id": "rm_milk_whole", "qty": 200.0},
        {"rm_id": "rm_cup_12oz", "qty": 1.0},
        {"rm_id": "rm_lid_12oz", "qty": 1.0},
    ],
    "prod_cold_brew": [
        {"rm_id": "rm_coffee_ethiopia", "qty": 25.0},
        {"rm_id": "rm_cup_12oz", "qty": 1.0},
        {"rm_id": "rm_lid_12oz", "qty": 1.0},
    ],
    "prod_soda": [
        {"rm_id": "rm_bottle_soda", "qty": 1.0},
    ],
    "prod_ayran": [
        {"rm_id": "rm_bottle_ayran", "qty": 1.0},
    ],
    "prod_toast_cheese": [
        {"rm_id": "rm_bread_toast", "qty": 2.0},    # 2 dilim ekmek
        {"rm_id": "rm_cheese_kasar", "qty": 60.0},  # 60 gram kaşar
        {"rm_id": "rm_butter", "qty": 10.0},        # 10 gram tereyağı
    ],
    "prod_toast_mixed": [
        {"rm_id": "rm_bread_toast", "qty": 2.0},    # 2 dilim ekmek
        {"rm_id": "rm_cheese_kasar", "qty": 45.0},  # 45 gram kaşar
        {"rm_id": "rm_sucuk", "qty": 35.0},         # 35 gram sucuk
        {"rm_id": "rm_butter", "qty": 10.0},        # 10 gram tereyağı
    ],
    "prod_san_sebastian": [
        {"rm_id": "rm_cake_san_sebastian", "qty": 1.0},
    ],
    "prod_croissant": [
        {"rm_id": "rm_croissant", "qty": 1.0},
    ],
}

# 5. SALON MASALARI
DINING_TABLES = [
    {"id": "tbl_s1", "name": "Masa 1 (Salon)", "category": "Salon"},
    {"id": "tbl_s2", "name": "Masa 2 (Salon)", "category": "Salon"},
    {"id": "tbl_s3", "name": "Masa 3 (Salon)", "category": "Salon"},
    {"id": "tbl_s4", "name": "Masa 4 (Salon)", "category": "Salon"},
    {"id": "tbl_s5", "name": "Masa 5 (Salon)", "category": "Salon"},
    {"id": "tbl_s6", "name": "Masa 6 (Salon)", "category": "Salon"},
    {"id": "tbl_b1", "name": "Bahçe 1", "category": "Bahçe"},
    {"id": "tbl_b2", "name": "Bahçe 2", "category": "Bahçe"},
    {"id": "tbl_b3", "name": "Bahçe 3", "category": "Bahçe"},
    {"id": "tbl_b4", "name": "Bahçe 4", "category": "Bahçe"},
    {"id": "tbl_o1", "name": "Okey 1 (Oyun)", "category": "Oyun"},
    {"id": "tbl_o2", "name": "Okey 2 (Oyun)", "category": "Oyun"},
    {"id": "tbl_o3", "name": "Okey 3 (Oyun)", "category": "Oyun"},
    {"id": "tbl_o4", "name": "Okey 4 (Oyun)", "category": "Oyun"},
    {"id": "tbl_pos", "name": "Kasa / Gel-Al", "category": "Paket"},
]

# 6. PERSONEL VE HIZLI GİRİŞ PIN KODLARI
STAFF = [
    {"id": "stf_1", "name": "Ahmet Yılmaz", "role": "Garson", "pin": "1001"},
    {"id": "stf_2", "name": "Elif Şahin", "role": "Garson", "pin": "1002"},
    {"id": "stf_3", "name": "Mehmet Kaya", "role": "Kasiyer", "pin": "2001"},
    {"id": "stf_4", "name": "Can Demir", "role": "Barista / Çaycı", "pin": "3001"},
    {"id": "stf_5", "name": "Zeynep Çelik", "role": "Yönetici (Patron)", "pin": "9999"},
]

def generate_orders(days=180):
    """Son 6 ayın çay, tost, kahve ve masa ağırlıklı gerçekçi sipariş geçmişini üretir."""
    orders = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    weather_types = ["Güneşli", "Bulutlu", "Yağmurlu", "Rüzgarlı"]

    current_date = start_date
    order_counter = 1000

    while current_date <= end_date:
        weekday = current_date.weekday()
        is_weekend = weekday in [5, 6]
        is_wednesday = (weekday == 2)

        weather = random.choices(weather_types, weights=[50, 25, 20, 5])[0]
        temp = random.randint(15, 30)
        if weather == "Yağmurlu":
            temp = random.randint(10, 18)

        # Günlük sipariş tabanı
        base_orders = random.randint(140, 190)
        if is_weekend:
            base_orders = int(base_orders * 1.55) # Hafta sonu okey ve kafe yoğunluğu
        if is_wednesday:
            base_orders = int(base_orders * 1.35) # Hafta içi Çarşamba yoğunluğu

        if weather == "Yağmurlu":
            base_orders = int(base_orders * 1.20) # Yağmurda kafeye sığınanlar ve çay/tost artışı

        for _ in range(base_orders):
            order_counter += 1
            
            # Saat dağılımı (Sabah çay/tost, öğle molası, ikindi çayı ve akşam okey/sohbet)
            hour_weights = [
                0, 0, 0, 0, 0, 0, 0, 0,  # 00-07 kapalı
                6, 8, 7, 9,             # 08-11 sabah çay & tost
                15, 14,                 # 12-13 öğle tostu ve kahveler
                10, 14, 18, 17,         # 14-17 ikindi çayı & kahve/tatlı
                14, 13, 11, 6,          # 18-21 akşam okey/sohbet (seri çay & soda)
                2, 0                    # 22-23 kapanış
            ]
            hour = random.choices(range(24), weights=hour_weights)[0]
            minute = random.randint(0, 59)
            order_time = current_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))

            # Masa seçimi (Oyun masalarında çay ve soda ağırlıklıdır)
            chosen_table = random.choice(DINING_TABLES)
            is_game_table = (chosen_table["category"] == "Oyun")

            # Ürün seçimi ağırlıkları
            weights = []
            for p in PRODUCTS:
                w = 10
                # Çay ve Türk Kahvesi her zaman kafenin en çok satan lokomotifidir
                if p["id"] == "prod_tea_glass":
                    w = 60 if is_game_table else 45
                elif p["id"] == "prod_tea_pot":
                    w = 15 if (is_game_table or is_weekend) else 6
                elif p["id"] == "prod_turkish_coffee":
                    w = 20
                elif p["id"] == "prod_soda":
                    w = 25 if is_game_table else 15
                elif p["id"] == "prod_toast_cheese" or p["id"] == "prod_toast_mixed":
                    w = 30 if hour in [8, 9, 10, 12, 13, 16, 17] else 8
                elif p["type"] == "cold" and temp >= 22:
                    w = 22
                elif p["type"] == "hot" and (temp < 18 or weather == "Yağmurlu"):
                    w = 25
                elif p["type"] == "food" and "toast" not in p["id"]:
                    w = 8 if hour in [14, 15, 16, 17] else 3
                weights.append(w)

            # Sepette 1 ila 4 ürün (Özellikle masada oturanlar birden fazla çay/tost söyler)
            item_count = random.choices([1, 2, 3, 4], weights=[45, 35, 15, 5])[0]
            chosen_products = random.choices(PRODUCTS, weights=weights, k=item_count)

            order_items = []
            total_price = 0.0
            for cp in chosen_products:
                qty = 1
                # Çay masada genelde 2'şer 3'er söylenir
                if cp["id"] == "prod_tea_glass" and random.random() < 0.4:
                    qty = random.choice([2, 3, 4])
                price = cp["price"]
                item_total = price * qty
                total_price += item_total
                order_items.append({
                    "product_id": cp["id"],
                    "product_name": cp["name"],
                    "quantity": qty,
                    "unit_price": price
                })

            payment_method = random.choices(["Kredi Kartı", "Nakit"], weights=[65, 35])[0]
            # Siparişi alan garson/kasiyer
            waiters = [s for s in STAFF if s["role"] in ["Garson", "Kasiyer"]]
            server = random.choice(waiters)

            orders.append({
                "order_id": f"ORD-{order_counter}",
                "timestamp": order_time.strftime("%Y-%m-%d %H:%M:%S"),
                "table_id": chosen_table["id"],
                "table_name": chosen_table["name"],
                "weekday": current_date.strftime("%A"),
                "weather": weather,
                "temperature": temp,
                "staff_name": server["name"],
                "staff_pin": server["pin"],
                "payment_method": payment_method,
                "total_amount": round(total_price, 2),
                "items": order_items
            })

        current_date += timedelta(days=1)

    return orders

def save_to_sqlite(data):
    """Verileri SQLite veritabanına aktarır."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(OUTPUT_DB)
    cur = conn.cursor()

    # Eski tablolar varsa kaldir ve temiz olustur
    cur.execute("DROP TABLE IF EXISTS raw_materials")
    cur.execute("DROP TABLE IF EXISTS products")
    cur.execute("DROP TABLE IF EXISTS dining_tables")
    cur.execute("DROP TABLE IF EXISTS staff")
    cur.execute("DROP TABLE IF EXISTS orders")
    cur.execute("DROP TABLE IF EXISTS order_items")

    cur.execute("""
    CREATE TABLE raw_materials (
        id TEXT PRIMARY KEY,
        name TEXT,
        category TEXT,
        unit TEXT,
        current_stock REAL,
        min_alert REAL,
        cost REAL
    )
    """)

    cur.execute("""
    CREATE TABLE products (
        id TEXT PRIMARY KEY,
        cat_id TEXT,
        name TEXT,
        price REAL,
        type TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE dining_tables (
        id TEXT PRIMARY KEY,
        name TEXT,
        category TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE staff (
        id TEXT PRIMARY KEY,
        name TEXT,
        role TEXT,
        pin TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,
        timestamp TEXT,
        table_id TEXT,
        table_name TEXT,
        weekday TEXT,
        weather TEXT,
        temperature INTEGER,
        staff_name TEXT,
        staff_pin TEXT,
        payment_method TEXT,
        total_amount REAL
    )
    """)

    cur.execute("""
    CREATE TABLE order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        product_id TEXT,
        product_name TEXT,
        quantity INTEGER,
        unit_price REAL
    )
    """)

    for rm in data["raw_materials"]:
        cur.execute("INSERT INTO raw_materials VALUES (?,?,?,?,?,?,?)",
                    (rm["id"], rm["name"], rm["category"], rm["unit"], rm["current_stock"], rm["min_alert"], rm["cost"]))

    for p in data["products"]:
        cur.execute("INSERT INTO products VALUES (?,?,?,?,?)",
                    (p["id"], p["cat_id"], p["name"], p["price"], p["type"]))

    for t in data["dining_tables"]:
        cur.execute("INSERT INTO dining_tables VALUES (?,?,?)",
                    (t["id"], t["name"], t["category"]))

    for s in data["staff"]:
        cur.execute("INSERT INTO staff VALUES (?,?,?,?)",
                    (s["id"], s["name"], s["role"], s["pin"]))

    for o in data["orders"]:
        cur.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (o["order_id"], o["timestamp"], o["table_id"], o["table_name"], o["weekday"], o["weather"], o["temperature"], o["staff_name"], o["staff_pin"], o["payment_method"], o["total_amount"]))
        for it in o["items"]:
            cur.execute("INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price) VALUES (?,?,?,?,?)",
                        (o["order_id"], it["product_id"], it["product_name"], it["quantity"], it["unit_price"]))

    conn.commit()
    conn.close()

def main():
    print("[*] CafeERP gercekci kafe veri seti (Cay, Tost, Kahve, Masalar, Personel PIN) olusturuluyor...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    orders = generate_orders(days=180)
    
    full_data = {
        "cafe_info": {
            "name": "Artisan & Keyif Cafe",
            "type": "Modern & Geleneksel Hibrit Kafe",
            "city": "Istanbul"
        },
        "raw_materials": RAW_MATERIALS,
        "categories": CATEGORIES,
        "products": PRODUCTS,
        "recipes": RECIPES,
        "dining_tables": DINING_TABLES,
        "staff": STAFF,
        "total_orders_generated": len(orders),
        "orders": orders
    }

    # JSON Olarak Kaydet
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)

    # SQLite Olarak Kaydet
    save_to_sqlite(full_data)

    print(f"[OK] Basarili! {len(orders)} adet siparis uretildi.")
    print(f"JSON Dosyasi: {OUTPUT_JSON}")
    print(f"SQLite Veritabani: {OUTPUT_DB}")

if __name__ == "__main__":
    main()
