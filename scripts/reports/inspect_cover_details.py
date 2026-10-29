from _paths import IMAGE_DIR, OUTPUT_PATH, TEMPLATE_PATH

import docx

doc = docx.Document(TEMPLATE_PATH)

for i in range(35):
    p = doc.paragraphs[i]
    pf = p.paragraph_format
    r_fonts = [f"{r.font.name} {r.font.size.pt if r.font.size else 'None'}pt" for r in p.runs]
    print(f"P[{i:02d}]: text='{p.text[:30]}' runs={r_fonts} space_before={pf.space_before} space_after={pf.space_after} line_spacing={pf.line_spacing}")
