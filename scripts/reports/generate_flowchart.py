from _paths import IMAGE_DIR, OUTPUT_PATH, TEMPLATE_PATH

import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Set font family to serif (Times New Roman)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']

fig, ax = plt.subplots(figsize=(10.5, 14.5), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(0, 150)
ax.axis('off')

# Styling constants
c_phase_bg = '#f8fafc'
c_box_bg = '#ffffff'
c_box_border = '#1e3d59'
c_title_text = '#0f172a'
c_accent = '#1e3d59'

def draw_phase_card(y_top, height, title, step_num):
    # Phase background card
    rect = patches.FancyBboxPatch((5, y_top - height), 90, height,
                                  boxstyle="round,pad=1.0,rounding_size=2.0",
                                  facecolor=c_phase_bg, edgecolor='#cbd5e1', linewidth=1.1, zorder=1)
    ax.add_patch(rect)
    # Title badge
    badge = patches.FancyBboxPatch((8, y_top - 4.5), 84, 5.0,
                                  boxstyle="round,pad=0.6,rounding_size=1.2",
                                  facecolor=c_accent, edgecolor='none', zorder=2)
    ax.add_patch(badge)
    ax.text(50, y_top - 2.0, f"{step_num}. AŞAMA: {title.upper()}",
            ha='center', va='center', color='white', fontsize=10.5, fontweight='bold', zorder=3)

def draw_box(x, y, w, h, title, lines=None, fill_color=c_box_bg, border_color=c_box_border, is_sub=False):
    rect = patches.FancyBboxPatch((x, y - h), w, h,
                                  boxstyle="round,pad=0.7,rounding_size=1.4",
                                  facecolor=fill_color, edgecolor=border_color, linewidth=1.1, zorder=4)
    ax.add_patch(rect)

    if lines:
        title_y = y - 2.5
        ax.text(x + w/2, title_y, title, ha='center', va='center', color=c_title_text,
                fontsize=9.8, fontweight='bold', zorder=5)
        line_spacing = (h - 3.8) / (len(lines) + 0.2)
        for i, line in enumerate(lines):
            cur_y = y - 4.2 - (i * line_spacing)
            ax.text(x + w/2, cur_y, line, ha='center', va='center',
                    color='#475569', fontsize=8.6, zorder=5)
    else:
        ax.text(x + w/2, y - h/2, title, ha='center', va='center', color=c_title_text,
                fontsize=9.8, fontweight='bold', zorder=5)

def draw_arrow(x1, y1, x2, y2, label=None, label_side='right'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color='#1e3d59', lw=1.5, mutation_scale=13),
                zorder=6)
    if label:
        lx = (x1 + x2) / 2
        ly = (y1 + y2) / 2
        offset_x = 2.0 if label_side == 'right' else -2.0
        ha = 'left' if label_side == 'right' else 'right'
        ax.text(lx + offset_x, ly, label, ha=ha, va='center',
                fontsize=8.3, color='#1e3d59', style='italic', zorder=7)

# --- 1. AŞAMA (Y: 146 - 105) ---
draw_phase_card(146, 41, "Sistem Mimarisi ve Veri Tabanı Tasarımı", "1")

# Clients
draw_box(9, 136, 25, 7.5, "Kasa / POS Terminali", ["Dokunmatik Adisyon Arayüzü"])
draw_box(37.5, 136, 25, 7.5, "Mobil Garson Terminali", ["Masada Anlık Sipariş Girişi"])
draw_box(66, 136, 25, 7.5, "Mutfak / KDS Ekranı", ["Canlı Hazırlık Takibi"])

# Arrows to Backend
draw_arrow(21.5, 128.5, 34, 122.5)
draw_arrow(50, 128.5, 50, 122.5)
draw_arrow(78.5, 128.5, 66, 122.5)

# Backend
draw_box(20, 122.5, 60, 7.5, "FastAPI Arka Uç (Backend Servisi)", ["REST API Rotaları ve WebSocket Eşzamanlı Haberleşme"])

# Arrow to DB
draw_arrow(50, 115, 50, 112, label="ORM / SQL", label_side='right')

# Database
draw_box(14, 112, 72, 6.8, "İlişkisel Veri Tabanı (PostgreSQL / SQLite)",
         ["Masalar, Siparişler, Menü Varyasyonları, Reçeteler (BOM) ve Hammadde Stokları"])

# Arrow between Phase 1 and Phase 2
draw_arrow(50, 105, 50, 99)

# --- 2. AŞAMA (Y: 99 - 58) ---
draw_phase_card(99, 41, "Veri Hazırlama ve Model Eğitimi", "2")

# Data Sources
draw_box(11, 89, 36, 7.5, "Geçmiş Satış Kayıtları", ["37.000+ İşlem / 6 Aylık Kafe Verisi"])
draw_box(53, 89, 36, 7.5, "Open-Meteo Hava Durumu API", ["Sıcaklık, Yağış ve Günlük Hava Kodu"])

# Arrows to Feature Engineering
draw_arrow(29, 81.5, 38, 76.5)
draw_arrow(71, 81.5, 62, 76.5)

# Feature Engineering
draw_box(16, 76.5, 68, 7.5, "Öznitelik Mühendisliği (Feature Engineering)",
         ["Tarih, Gün, Hafta Sonu, Saat Dilimi ve Meteorolojik Değişkenler"])

# Arrow to Model
draw_arrow(50, 69, 50, 65.5, label="Eğitim Veri Seti", label_side='right')

# LightGBM Model
draw_box(16, 65.5, 68, 6.8, "LightGBM Makine Öğrenmesi Modeli",
         ["Ürün Bazlı Model Eğitimi -> Saatlik ve Günlük Talep Tahmini"])

# Arrow between Phase 2 and Phase 3
draw_arrow(50, 58, 50, 52)

# --- 3. AŞAMA (Y: 52 - 6) ---
draw_phase_card(52, 46, "Reçete Motoru ve Karar Destek Mantığı", "3")

# Inputs
draw_box(9, 42, 38, 7.5, "Sipariş Onayı (POS / Mobil)", ["Adisyon Kesildiği Anda Tetikleme"])
draw_box(53, 42, 38, 7.5, "Yapay Zeka Talep Tahmini", ["Gelecek Saatlerin Beklenen Satış Miktarı"])

# Down arrows
draw_arrow(28, 34.5, 28, 31)
draw_arrow(72, 34.5, 72, 31)

# Processing
draw_box(9, 31, 38, 7.5, "Dinamik Reçete Motoru", ["Gramaj / ml Bazlı Otomatik Stok Düşümü"])
draw_box(53, 31, 38, 7.5, "Tüketim Hızı (Burn-Rate) Hesabı", ["Mevcut Stok ve Tahmini Tüketim Kıyaslaması"])

# Arrows to Decision Engine
draw_arrow(28, 23.5, 41, 19.5)
draw_arrow(72, 23.5, 59, 19.5)

# Decision Engine
draw_box(16, 19.5, 68, 7.2, "Kural Tabanlı Uzman Karar Motoru",
         ["Kritik Eşik Seviyesi ve Yaklaşan Stok Tükenme Riski Denetimi"])

# Arrow to Telegram
draw_arrow(50, 12.3, 50, 9.5)

# Telegram Output Box
draw_box(16, 9.5, 68, 6.2, "Telegram Botu - İşletmeci Karar Desteği",
         ["Anlık Stok Tükenme Bildirimi ve Akıllı Satın Alma Önerisi"],
         fill_color='#f0f9ff', border_color='#0284c7')

plt.tight_layout()
output_img = IMAGE_DIR / "yontem_akis_semasi.png"
plt.savefig(output_img, bbox_inches='tight', dpi=300)

print(f"Grafik basariyla uretildi: {output_img}")
