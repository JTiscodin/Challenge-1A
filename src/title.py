def extract_title(page):
    import unicodedata
    def is_latin(text):
        latin_count = sum('LATIN' in unicodedata.name(c, '') for c in text if c.isalpha())
        total_alpha = sum(1 for c in text if c.isalpha())
        return total_alpha > 0 and latin_count > total_alpha // 2

    blocks = page.get_text("dict")['blocks']
    spans = []
    page_height = page.rect.height
    page_width = page.rect.width
    for block in blocks:
        for line in block.get('lines', []):
            for span in line['spans']:
                text = span['text'].strip()
                if text:
                    spans.append({
                        'text': text,
                        'size': span['size'],
                        'bbox': span['bbox'],
                        'y0': span['bbox'][1],
                        'x0': span['bbox'][0],
                        'x1': span['bbox'][2],
                        'bold': (span['flags'] & 2 != 0),
                        'page_width': page_width,
                        'font': span.get('font', None)
                    })
    if not spans:
        return ""
    max_size = max(s['size'] for s in spans)
    top_spans = [s for s in spans if s['y0'] < page_height * 0.5]
    for s in top_spans:
        s['score'] = 0  # heading_score(s, max_size, page_height, is_title_candidate=True)  # To be imported if needed
    if not top_spans:
        return spans[0]['text']
    top_spans.sort(key=lambda s: (-s.get('score', 0), s['y0']))
    best = top_spans[0]
    all_top_spans = [s for s in spans if s['y0'] < page_height * 0.5]
    all_top_spans.sort(key=lambda s: s['y0'])
    idx = next(i for i, s in enumerate(all_top_spans) if s['y0'] == best['y0'] and s['text'] == best['text'])
    title_lines = [best['text']]
    last_y = best['y0']
    base_font = best['font']
    base_size = best['size']
    is_latin_title = is_latin(best['text'])
    for s in all_top_spans[idx+1:]:
        if is_latin_title:
            if (
                s['font'] == base_font and
                abs(s['size'] - base_size) < 1.0 and
                abs(s['y0'] - last_y) < 120
            ):
                title_lines.append(s['text'])
                last_y = s['y0']
            else:
                break
        else:
            if (
                s['font'] == base_font and
                abs(s['size'] - base_size) < 2.0 and
                abs(s['y0'] - last_y) < 120
            ):
                title_lines.append(s['text'])
                last_y = s['y0']
            else:
                break
    return " ".join(title_lines) 