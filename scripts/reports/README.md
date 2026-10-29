# Rapor araçları

Bu klasör uygulamadan bağımsız akademik rapor ve görsel yardımcılarını içerir.
Komutları proje kökünden çalıştırın:

```powershell
python scripts/reports/generate_chart.py
python scripts/reports/generate_flowchart.py
python scripts/reports/build_clean_doc.py
```

- `generate_chart.py`, `generate_flowchart.py`: `docs/images/` içine görsel üretir.
- `build_clean_doc.py`: Word şablonundan düzenlenmiş rapor üretir.
- `fix_report_layout.py`: şablona alternatif yerleşim düzeltmesi uygular.
- `inspect_*.py`, `extract_all_texts.py`: şablonun yapısını ve metinlerini inceler.
- `_paths.py`: ortak yolları ve konsol kodlamasını tanımlar.

Word şablonunu `docs/templates/` altına yerleştirin veya `CAFE_REPORT_TEMPLATE`
ortam değişkeniyle seçin. Word çıktıları `docs/output/` içine yazılır.
Şablon ve üretilen belgeler Git'e eklenmez. Araçlar mevcut rapor şablonunun
paragraf ve tablo düzenine özeldir. Bağımlılıklar kökteki `requirements.txt` içindedir.
