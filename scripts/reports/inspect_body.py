from _paths import IMAGE_DIR, OUTPUT_PATH, TEMPLATE_PATH

import docx

doc = docx.Document(TEMPLATE_PATH)

body_elements = doc.element.body

print(f"Total body children: {len(body_elements)}")
for i, el in enumerate(body_elements):
    tag = el.tag.split('}')[-1]
    if tag == 'p':
        p = docx.text.paragraph.Paragraph(el, doc)
        text_snippet = p.text.strip().replace('\n', ' ')[:50]
        has_drawing = len(el.xpath('.//w:drawing')) > 0
        has_pagebreak = len(el.xpath('.//w:br[@w:type="page"]')) > 0
        print(f"[{i:02d}] P: text='{text_snippet}' (len={len(p.text)}) img={has_drawing} pb={has_pagebreak}")
    elif tag == 'tbl':
        tbl = docx.table.Table(el, doc)
        first_row_text = tbl.rows[0].cells[0].text.strip().replace('\n', ' ')[:50]
        print(f"[{i:02d}] TBL: rows={len(tbl.rows)} cols={len(tbl.columns)} first='{first_row_text}'")
    elif tag == 'sectPr':
        print(f"[{i:02d}] sectPr (section properties)")
    else:
        print(f"[{i:02d}] {tag}")
