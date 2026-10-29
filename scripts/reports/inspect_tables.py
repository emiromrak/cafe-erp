from _paths import IMAGE_DIR, OUTPUT_PATH, TEMPLATE_PATH

import docx

doc = docx.Document(TEMPLATE_PATH)

for i, table in enumerate(doc.tables):
    print(f"\n--- TABLE {i} ---")
    for r_idx, row in enumerate(table.rows):
        for c_idx, cell in enumerate(row.cells):
            # check shading / borders / styles
            shading = cell._tc.get_or_add_tcPr().find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd')
            shd_val = shading.attrib if shading is not None else None
            text_snippet = cell.text.strip().replace('\n', ' ')[:40]
            print(f"  R{r_idx}C{c_idx}: shd={shd_val} text='{text_snippet}'")
