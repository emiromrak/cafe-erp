from _paths import IMAGE_DIR, OUTPUT_PATH, TEMPLATE_PATH

import docx

doc = docx.Document(TEMPLATE_PATH)

print("--- COVER PAGE PARAGRAPHS (0 to 34) ---")
for i in range(35):
    p = doc.paragraphs[i]
    has_img = len(p._element.xpath('.//a:blip')) > 0 or len(p._element.xpath('.//w:drawing')) > 0
    print(f"P[{i}]: text='{p.text}' align={p.alignment} style={p.style.name} img={has_img}")
