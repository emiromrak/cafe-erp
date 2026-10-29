from _paths import IMAGE_DIR, OUTPUT_PATH, TEMPLATE_PATH

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Polygon
import numpy as np

# Set font family to Times New Roman if available
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Liberation Serif']
plt.rcParams['mathtext.fontset'] = 'stix'

# Tasks definition
# (name, start_month, end_month, category)
# Categories: 'prep' (gray), 'core' (navy), 'ext' (light blue), 'ext_cond' (hatched)
tasks = [
    ("Gereksinim ve veri kaynağı doğrulama", 0.0, 1.0, "prep"),
    ("Mimari, veri modeli, arayüz taslakları", 0.4, 1.0, "prep"),
    ("Çekirdek FastAPI iskeleti ve yerel veritabanı (Ç1)", 1.0, 2.0, "core"),
    ("Menü, varyasyon ve reçete yapısı (Ç2)", 1.0, 2.2, "core"),
    ("Sipariş ve adisyon kayıt motoru (Ç3)", 1.8, 3.0, "core"),
    ("Stok ve kritik seviye takip motoru (Ç4)", 2.4, 3.6, "core"),
    ("Geçmiş satış verisi ve hava durumu veri boru hattı", 2.8, 4.0, "core"),
    ("Asistan: LightGBM talep tahmini ve kurallar (Ç5)", 3.4, 4.5, "core"),
    ("Asistan test kümesi ve ilk hata ölçümü (MAE/RMSE)", 3.8, 4.5, "core"),
    ("Hava durumu API entegrasyonu (Ç6)", 3.8, 4.3, "core"),
    ("Dönemsel özet rapor ve işletmeci analizleri (Ç7)", 4.3, 5.0, "core"),
    ("Kasa POS ve mobil garson arayüzü (G1, G2)", 5.0, 6.0, "ext"),
    ("Canlı eşitleme ve Telegram asistanı (G3, G4)", 5.0, 6.0, "ext_cond"),
    ("Sistem, çevrimdışı ve kullanılabilirlik testleri", 6.0, 6.7, "prep"),
    ("Karar motorunun nihai saha değerlendirmesi", 6.5, 7.2, "prep"),
    ("Hata düzeltme ve yedek süre", 6.8, 8.0, "prep"),
    ("Nihai rapor ve sunum", 6.0, 8.0, "prep")
]

# Total tasks
n_tasks = len(tasks)

# Colors matching the image
c_prep = '#7b838a'       # gray
c_core = '#1e4875'       # dark navy blue
c_ext = '#85b3d6'        # soft light blue
c_diamond = '#c04a18'    # reddish-orange for milestones
c_grid = '#f0f2f5'       # alternating background row

fig, ax = plt.subplots(figsize=(13.5, 8.2), dpi=300)

# Invert Y axis so first task is on top
y_positions = np.arange(n_tasks)

# Draw alternating background bands
for i in range(n_tasks):
    if i % 2 == 0:
        ax.axhspan(i - 0.45, i + 0.45, color=c_grid, zorder=0, alpha=0.7)

# Draw milestone vertical dashed lines
milestones = [
    (1.0, "K1", "Ekim Sonu"),
    (4.0, "K2", "Ocak Sonu"),
    (6.0, "K3", "Mart Sonu"),
    (7.0, "K4", "Nisan Sonu")
]

for m_pos, m_label, m_sub in milestones:
    ax.axvline(x=m_pos, color=c_diamond, linestyle='--', linewidth=1.1, zorder=1, alpha=0.85)

# Plot task bars
bar_height = 0.55
for idx, (t_name, start, end, cat) in enumerate(tasks):
    width = end - start
    y = idx
    if cat == "prep":
        ax.barh(y, width, left=start, height=bar_height, color=c_prep, edgecolor='none', zorder=3)
    elif cat == "core":
        ax.barh(y, width, left=start, height=bar_height, color=c_core, edgecolor='none', zorder=3)
    elif cat == "ext":
        ax.barh(y, width, left=start, height=bar_height, color=c_ext, edgecolor='none', zorder=3)
    elif cat == "ext_cond":
        # Hatched bar
        ax.barh(y, width, left=start, height=bar_height, color=c_ext, hatch='//', edgecolor=c_core, linewidth=1.0, zorder=3)

# Formatting axes
ax.set_ylim(n_tasks - 0.5, -0.8)
ax.set_xlim(-0.1, 8.1)

# Y-ticks
ax.set_yticks(y_positions)
ax.set_yticklabels([t[0] for t in tasks], fontsize=10.5, color='#2c3e50')
ax.tick_params(axis='y', length=0, pad=12)

# X-ticks (Months)
month_names = ["Ekim", "Kasım", "Aralık", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs"]
x_ticks = np.arange(0.5, 8.5, 1.0)
ax.set_xticks(x_ticks)
ax.set_xticklabels([f"Ay {i+1}\n({m})" for i, m in enumerate(month_names)], fontsize=10.5, fontweight='normal', color='#2c3e50')

# Place X-axis on top
ax.xaxis.tick_top()
ax.xaxis.set_label_position('top')

# Subtitle / Top label
ax.text(-0.08, -0.65, "Süreç", fontsize=11, fontweight='bold', color='#1a252f', va='center', ha='left')

# Hide unnecessary spines
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color('#bdc3c7')
ax.spines['top'].set_color('#2c3e50')
ax.spines['top'].set_linewidth(1.2)

# Subtle vertical grid lines for month boundaries
for x in range(1, 9):
    ax.axvline(x=x, color='#e2e6ea', linewidth=0.8, zorder=1)

# Bottom section: Karar Noktaları (K1, K2, K3, K4)
# Add milestone diamonds and text below the plot area
ax.text(-0.08, n_tasks + 0.6, "Karar noktaları (ay sonu)", fontsize=10.5, color='#2c3e50', va='center', ha='left')

for m_pos, m_label, m_sub in milestones:
    # Plot diamond
    ax.scatter(m_pos, n_tasks + 0.6, marker='D', s=130, color=c_diamond, zorder=4, edgecolor='white', linewidth=1)
    ax.text(m_pos, n_tasks + 1.15, m_label, fontsize=10.5, fontweight='bold', color=c_diamond, ha='center', va='center')

# Bottom legend
legend_y = n_tasks + 2.0

# Items: (label, color, hatch, edge)
leg_items = [
    ("Hazırlık, doğrulama ve teslim", c_prep, None, 'none'),
    ("Çekirdek", c_core, None, 'none'),
    ("Genişletilmiş", c_ext, None, 'none'),
    ("Genişletilmiş (koşullu)", c_ext, '//', c_core)
]

start_x = 0.0
step_x = 2.1
for idx, (label, col, hatch, edge) in enumerate(leg_items):
    lx = start_x + idx * step_x
    # Draw small rectangle patch
    rect = patches.Rectangle((lx, legend_y - 0.15), 0.35, 0.3, facecolor=col, hatch=hatch, edgecolor=edge if edge != 'none' else None, linewidth=0.8)
    ax.add_patch(rect)
    ax.text(lx + 0.42, legend_y, label, fontsize=9.5, color='#34495e', va='center', ha='left')

# Extend y-limit to include milestones and legend comfortably
ax.set_ylim(legend_y + 0.6, -0.9)

plt.tight_layout()
output_path = IMAGE_DIR / "calisma_takvimi_gantt.png"
plt.savefig(output_path, bbox_inches='tight', dpi=300)
print(f"Chart successfully saved to {output_path}")
