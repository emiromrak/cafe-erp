from _paths import IMAGE_DIR, OUTPUT_PATH, TEMPLATE_PATH

import docx

doc = docx.Document(TEMPLATE_PATH)

for i in range(1, 8):
    t = doc.tables[i]
    print(f"\n=== Table {i} ===")
    print(f"tblPr XML: {t._tbl.tblPr.xml}")
    for r_idx, row in enumerate(t.rows):
        trPr = row._tr.trPr
        trPr_xml = trPr.xml if trPr is not None else "None"
        cell = row.cells[0]
        tcPr = cell._tc.tcPr
        tcPr_xml = tcPr.xml if tcPr is not None else "None"
        text = cell.text.strip().replace('\n', ' ')[:40]
        print(f"  Row {r_idx}: trPr={trPr_xml} | text='{text}'")
