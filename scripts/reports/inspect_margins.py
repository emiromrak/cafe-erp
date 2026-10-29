from _paths import IMAGE_DIR, OUTPUT_PATH, TEMPLATE_PATH

import docx

doc = docx.Document(TEMPLATE_PATH)
sec = doc.sections[0]

print("Page width:", sec.page_width.cm, "cm")
print("Page height:", sec.page_height.cm, "cm")
print("Top margin:", sec.top_margin.cm, "cm")
print("Bottom margin:", sec.bottom_margin.cm, "cm")
print("Left margin:", sec.left_margin.cm, "cm")
print("Right margin:", sec.right_margin.cm, "cm")
