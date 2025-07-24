import fitz
import json
from .headings import (cluster_font_sizes, get_header_footer_texts, detect_headings, apply_post_processing_filters)
from .title import extract_title

def process_pdf(pdf_path, output_path, allow_common_section_duplicates=True, custom_common_sections=None):
    doc = fitz.open(pdf_path)
    # Gather all font sizes
    sizes = []
    for page in doc:
        blocks = page.get_text("dict")['blocks']
        for block in blocks:
            for line in block.get('lines', []):
                for span in line['spans']:
                    sizes.append(span['size'])
    if not sizes:
        sizes = [12, 10, 8]
    thresholds = cluster_font_sizes(sizes)
    header_footer_texts = get_header_footer_texts(doc)
    title = extract_title(doc[0]) if len(doc) > 0 else ""
    outline = []
    for page in doc:
        max_size = 0
        blocks = page.get_text("dict")['blocks']
        for block in blocks:
            for line in block.get('lines', []):
                for span in line['spans']:
                    max_size = max(max_size, span['size'])
        headings = detect_headings(page, thresholds, max_size)
        outline.extend(headings)
    outline = apply_post_processing_filters(outline, allow_common_section_duplicates, custom_common_sections)
    level_order = {'H1': 0, 'H2': 1, 'H3': 2}
    outline.sort(key=lambda h: (level_order.get(h['level'], 99), h['page'], h['y0']))
    clean_outline = []
    for heading in outline:
        clean_outline.append({
            'level': heading['level'],
            'text': heading['text'],
            'page': heading['page']
        })
    result = {
        "title": title,
        "outline": clean_outline
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False) 