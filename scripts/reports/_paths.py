"""Rapor araçlarının ortak dosya yolları ve Windows konsol ayarları."""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
IMAGE_DIR = ROOT_DIR / 'docs' / 'images'
OUTPUT_DIR = ROOT_DIR / 'docs' / 'output'
TEMPLATE_PATH = Path(os.environ.get(
    'CAFE_REPORT_TEMPLATE',
    str(ROOT_DIR / 'docs' / 'templates' / 'tasarim-1-rapor-sablonu-13052025.docx'),
)).expanduser().resolve()
OUTPUT_PATH = OUTPUT_DIR / 'tasarim-1-rapor-sablonu-duzenlenmis.docx'

IMAGE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
