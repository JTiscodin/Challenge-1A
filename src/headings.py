import re
import numpy as np
from sklearn.cluster import KMeans
from collections import Counter

HEADING_PATTERNS = [
    re.compile(r'^(\d+\.)+\s+'),
    re.compile(r'^[A-Z]\.\s+'),
    re.compile(r'^[IVXLCDM]+\.\s+', re.IGNORECASE),
    re.compile(r'^[A-Z][A-Z\s\-]+$'),
]

def is_heading_pattern(text):
    for pat in HEADING_PATTERNS:
        if pat.match(text):
            return True
    return False

def cluster_font_sizes(sizes):
    arr = np.array(sizes).reshape(-1, 1)
    n_clusters = min(3, len(set(sizes)))
    if n_clusters < 2:
        return {"H1": max(sizes), "H2": min(sizes), "H3": min(sizes)}
    kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(arr)
    centers = sorted([c[0] for c in kmeans.cluster_centers_], reverse=True)
    thresholds = {"H1": centers[0], "H2": centers[1] if n_clusters > 1 else centers[0], "H3": centers[2] if n_clusters > 2 else centers[-1]}
    return thresholds

def get_header_footer_texts(doc):
    top_texts = []
    bottom_texts = []
    for page in doc:
        blocks = page.get_text("dict")['blocks']
        for block in blocks:
            for line in block.get('lines', []):
                for span in line['spans']:
                    text = span['text'].strip()
                    if not text:
                        continue
                    y0 = span['bbox'][1]
                    if y0 < 100:
                        top_texts.append(text)
                    elif y0 > 700:
                        bottom_texts.append(text)
    header = [t for t, c in Counter(top_texts).items() if c > len(doc) // 2]
    footer = [t for t, c in Counter(bottom_texts).items() if c > len(doc) // 2]
    return set(header + footer)

def heading_score(span, max_size, page_height, is_title_candidate=False):
    score = 0
    if abs(span['size'] - max_size) < 0.5:
        score += 8
    elif abs(span['size'] - max_size) < 2.0:
        score += 5
    elif abs(span['size'] - max_size) < 4.0:
        score += 2
    else:
        score -= 2
    if span['bold']:
        score += 4
    if is_heading_pattern(span['text']):
        score += 5
    page_width = span['page_width']
    x0, x1 = span['x0'], span['x1']
    if abs((x0 + x1)/2 - page_width/2) < 80:
        score += 3
    elif x0 < 100:
        score += 2
    else:
        score -= 3
    if span['text'].isupper() and len(span['text'].split()) >= 2:
        score += 3
    elif sum(1 for c in span['text'] if c.isupper()) >= 2:
        score += 1
    else:
        score -= 3
    wc = len(span['text'].split())
    if 2 <= wc <= 8:
        score += 2
    elif wc < 2 or wc > 12:
        score -= 4
    if is_title_candidate and span['y0'] < page_height * 0.25:
        score += 2
    if span['text'].endswith('.') and not is_heading_pattern(span['text']):
        score -= 3
    if len(span['text']) > 100:
        score -= 5
    return score

def detect_headings(page, thresholds, max_size):
    import unicodedata
    def is_latin(text):
        latin_count = sum('LATIN' in unicodedata.name(c, '') for c in text if c.isalpha())
        total_alpha = sum(1 for c in text if c.isalpha())
        return total_alpha > 0 and latin_count > total_alpha // 2
    headings = []
    blocks = page.get_text("dict")['blocks']
    page_width = page.rect.width
    page_height = page.rect.height
    all_spans = []
    for block in blocks:
        for line in block.get('lines', []):
            for span in line['spans']:
                text = span['text'].strip()
                if not text or len(text) < 1:
                    continue
                all_spans.append({
                    'text': text,
                    'size': span['size'],
                    'bbox': span['bbox'],
                    'y0': span['bbox'][1],
                    'y1': span['bbox'][3],
                    'x0': span['bbox'][0],
                    'x1': span['bbox'][2],
                    'bold': (span['flags'] & 2 != 0),
                    'page_width': page_width,
                    'font': span.get('font', None),
                    'flags': span['flags']
                })
    if not all_spans:
        return headings
    all_spans.sort(key=lambda s: s['y0'])
    font_sizes = [s['size'] for s in all_spans]
    unique_sizes = sorted(set(font_sizes), reverse=True)
    if max(unique_sizes) - min(unique_sizes) < 2.0:
        for span in all_spans:
            text = span['text']
            if is_bullet_point_or_subitem(text, span, all_spans):
                continue
            score = calculate_content_based_score(span, all_spans, page_height)
            if score >= 6:
                level = determine_heading_level_by_content(text, span, all_spans)
                if level:
                    headings.append({
                        'level': level,
                        'text': text,
                        'page': page.number + 1,
                        'score': score,
                        'y0': span['y0'],
                        'y1': span['y1'],
                        'x1': span['x1']
                    })
    else:
        h1_threshold = thresholds['H1']
        h2_threshold = thresholds['H2']
        h3_threshold = thresholds['H3']
        h1_range = (h1_threshold - 1.0, h1_threshold + 2.0)
        h2_range = (h2_threshold - 1.0, h2_threshold + 1.5)
        h3_range = (h3_threshold - 0.5, h3_threshold + 1.0)
        for span in all_spans:
            text = span['text']
            if is_bullet_point_or_subitem(text, span, all_spans):
                continue
            s = span.copy()
            s['score'] = heading_score(s, max_size, page_height)
            if s['score'] < 5:
                continue
            level = None
            if h1_range[0] <= s['size'] <= h1_range[1]:
                level = 'H1'
            elif h2_range[0] <= s['size'] <= h2_range[1]:
                level = 'H2'
            elif h3_range[0] <= s['size'] <= h3_range[1]:
                level = 'H3'
            else:
                if is_heading_pattern(text):
                    if s['size'] >= h2_threshold - 1.0:
                        level = 'H2'
                    else:
                        level = 'H3'
                else:
                    continue
            if not is_valid_heading_text(text):
                continue
            headings.append({
                'level': level,
                'text': text,
                'page': page.number + 1,
                'score': s['score'],
                'y0': s['y0'],
                'y1': s['y1'],
                'x1': s['x1']
            })
    return headings

def is_bullet_point_or_subitem(text, span, all_spans):
    if text.startswith('•') or text.startswith('-') or text.startswith('*'):
        return True
    if re.match(r'^\d+\.\s', text):
        return True
    if re.match(r'^[a-z]\.\s', text, re.IGNORECASE):
        return True
    for other_span in all_spans:
        if (other_span['y0'] < span['y0'] and 
            abs(other_span['y0'] - span['y0']) < 200 and
            other_span['x0'] < span['x0'] - 20):
            return True
    if (text.endswith('.') and len(text) > 50 and 
        not is_heading_pattern(text)):
        return True
    if text and text[0].islower() and not is_heading_pattern(text):
        return True
    return False

def calculate_content_based_score(span, all_spans, page_height):
    score = 0
    text = span['text']
    if span['y0'] < page_height * 0.3:
        score += 3
    elif span['y0'] < page_height * 0.6:
        score += 1
    page_width = span['page_width']
    x0, x1 = span['x0'], span['x1']
    if abs((x0 + x1)/2 - page_width/2) < 80:
        score += 3
    elif x0 < 100:
        score += 2
    else:
        score -= 2
    word_count = len(text.split())
    if 2 <= word_count <= 8:
        score += 4
    elif word_count == 1:
        score += 2
    elif word_count > 12:
        score -= 3
    if text.isupper() and word_count >= 2:
        score += 4
    elif sum(1 for c in text if c.isupper()) >= 2:
        score += 2
    else:
        score -= 2
    if span['bold']:
        score += 3
    if is_heading_pattern(text):
        score += 5
    if text.endswith('.') and not is_heading_pattern(text):
        score -= 4
    if text.count('.') > 1:
        score -= 3
    if len(text) > 100:
        score -= 3
    if (word_count >= 3 and word_count <= 8 and
        not text.endswith('.') and
        span['x0'] < 80 and
        sum(1 for c in text if c.isupper()) >= 3):
        score += 2
    return score

def determine_heading_level_by_content(text, span, all_spans):
    word_count = len(text.split())
    if (word_count >= 4 and word_count <= 10 and
        not text.endswith('.') and
        span['x0'] < 80 and
        sum(1 for c in text if c.isupper()) >= 3):
        return 'H1'
    elif (word_count >= 3 and word_count <= 8 and
          not text.endswith('.') and
          span['x0'] < 120 and
          sum(1 for c in text if c.isupper()) >= 2):
        return 'H2'
    elif (word_count >= 2 and word_count <= 6 and
          not text.endswith('.') and
          span['x0'] < 150):
        return 'H3'
    return None

def is_valid_heading_text(text):
    if len(text.strip()) < 3:
        return False
    if re.fullmatch(r'[ivxlcdm]+\.?', text.lower()) or \
       re.fullmatch(r'\(?[ivxlcdm]+\)?\.?', text.lower()) or \
       re.fullmatch(r'\(?\d+\)?\.?', text):
        return False
    if re.fullmatch(r'page\s+\d+', text.lower()) or \
       re.fullmatch(r'p\.\s*\d+', text.lower()) or \
       re.fullmatch(r'fig\.\s*\d+', text.lower()) or \
       re.fullmatch(r'table\s+\d+', text.lower()):
        return False
    digit_count = sum(1 for c in text if c.isdigit())
    if digit_count > len(text) * 0.5:
        return False
    if all(not c.isalnum() for c in text):
        return False
    if text.endswith('.') and not is_heading_pattern(text):
        return False
    if len(text) > 150:
        return False
    if sum(1 for c in text if c.islower()) > len(text) * 0.8 and not is_heading_pattern(text):
        return False
    if any(pattern in text.lower() for pattern in [
        'this is', 'there are', 'it is', 'they are', 'we can', 'you can',
        'the following', 'as follows', 'for example', 'such as'
    ]):
        return False
    return True

def merge_split_headings(headings):
    if not headings:
        return headings
    sorted_headings = sorted(headings, key=lambda h: (h['page'], h['y0']))
    merged = []
    i = 0
    while i < len(sorted_headings):
        current = sorted_headings[i]
        merged_text = current['text']
        j = i + 1
        while j < len(sorted_headings):
            next_heading = sorted_headings[j]
            if (next_heading['page'] == current['page'] and 
                next_heading['level'] == current['level'] and
                abs(next_heading['y0'] - current['y1']) < 30 and
                not current['text'].rstrip().endswith(('.', '!', '?', ':'))):
                merged_text += " " + next_heading['text']
                current['y1'] = next_heading['y1']
                current['x1'] = max(current['x1'], next_heading['x1'])
                j += 1
            else:
                break
        merged_heading = current.copy()
        merged_heading['text'] = merged_text.strip()
        merged.append(merged_heading)
        i = j
    return merged

def remove_duplicate_headings(headings, allow_common_section_duplicates=True, custom_common_sections=None):
    if not headings:
        return headings
    sorted_headings = sorted(headings, key=lambda h: (h['page'], h['y0']))
    default_common_sections = {
        'places to visit', 'attractions', 'things to do', 'what to see',
        'restaurants', 'hotels', 'accommodation', 'where to stay',
        'transportation', 'how to get there', 'getting around',
        'history', 'culture', 'traditions', 'customs',
        'food', 'cuisine', 'local dishes', 'dining',
        'shopping', 'markets', 'souvenirs',
        'nightlife', 'entertainment', 'activities',
        'tips', 'advice', 'recommendations', 'best time to visit',
        'weather', 'climate', 'when to go',
        'safety', 'security', 'travel tips',
        'costs', 'budget', 'expenses', 'prices'
    }
    if custom_common_sections:
        common_sections = custom_common_sections
    elif allow_common_section_duplicates:
        common_sections = default_common_sections
    else:
        common_sections = set()
    unique_headings = []
    seen_texts = {}
    for i, heading in enumerate(sorted_headings):
        text_norm = heading['text'].strip().lower()
        is_common_section = any(common in text_norm for common in common_sections)
        if text_norm in seen_texts:
            last_occurrence = seen_texts[text_norm]
            if is_common_section:
                parent_heading = None
                for j in range(i-1, -1, -1):
                    prev_heading = sorted_headings[j]
                    if prev_heading['level'] in ['H1', 'H2'] and prev_heading['page'] <= heading['page']:
                        parent_heading = prev_heading
                        break
                last_parent_heading = None
                for j in range(last_occurrence['index']-1, -1, -1):
                    prev_heading = sorted_headings[j]
                    if prev_heading['level'] in ['H1', 'H2'] and prev_heading['page'] <= last_occurrence['heading']['page']:
                        last_parent_heading = prev_heading
                        break
                if parent_heading and last_parent_heading and parent_heading['text'] != last_parent_heading['text']:
                    seen_texts[text_norm] = {
                        'heading': heading,
                        'index': i,
                        'parent': parent_heading['text']
                    }
                    unique_headings.append(heading)
                    continue
                else:
                    continue
            else:
                is_duplicate = False
                for existing_text in seen_texts:
                    if (text_norm in existing_text or existing_text in text_norm) and \
                       abs(len(text_norm) - len(existing_text)) < 10:
                        is_duplicate = True
                        break
                if is_duplicate:
                    continue
        seen_texts[text_norm] = {
            'heading': heading,
            'index': i,
            'parent': None
        }
        unique_headings.append(heading)
    return unique_headings

def validate_heading_hierarchy(headings):
    if not headings:
        return headings
    sorted_headings = sorted(headings, key=lambda h: (h['page'], h['y0']))
    validated = []
    level_order = {'H1': 1, 'H2': 2, 'H3': 3}
    last_level = 0
    last_h1_page = 0
    current_h1 = None
    for i, heading in enumerate(sorted_headings):
        current_level = level_order[heading['level']]
        current_page = heading['page']
        text = heading['text'].strip()
        if current_level > last_level + 1:
            if last_level == 1:
                heading['level'] = 'H2'
            elif last_level == 2:
                heading['level'] = 'H3'
            else:
                heading['level'] = 'H2'
        if current_page > last_h1_page + 1 and heading['level'] == 'H2':
            if (len(text.split()) <= 8 and 
                not text.endswith('.') and 
                sum(1 for c in text if c.isupper()) >= 2):
                heading['level'] = 'H1'
        if heading['level'] == 'H1':
            last_h1_page = current_page
            current_h1 = heading
        if heading['level'] == 'H2' and current_h1:
            if current_page > last_h1_page + 2:
                heading['level'] = 'H1'
                last_h1_page = current_page
                current_h1 = heading
        if heading['level'] == 'H3':
            has_h2_between = False
            for j in range(i-1, -1, -1):
                prev_heading = sorted_headings[j]
                if prev_heading['page'] < current_page:
                    break
                if prev_heading['level'] == 'H2':
                    has_h2_between = True
                    break
                elif prev_heading['level'] == 'H1':
                    break
            if not has_h2_between and current_h1:
                if (len(text.split()) >= 3 and 
                    not text.endswith('.') and 
                    sum(1 for c in text if c.isupper()) >= 2):
                    heading['level'] = 'H2'
        validated.append(heading)
        last_level = level_order[heading['level']]
    return validated

def filter_invalid_headings(headings):
    if not headings:
        return headings
    filtered = []
    for heading in headings:
        text = heading['text'].strip()
        if re.fullmatch(r'[ivxlcdm]+\.?', text.lower()) or \
           re.fullmatch(r'\(?[ivxlcdm]+\)?\.?', text.lower()) or \
           re.fullmatch(r'\(?\d+\)?\.?', text) or \
           len(text) < 3:
            continue
        if re.fullmatch(r'page\s+\d+', text.lower()) or \
           re.fullmatch(r'p\.\s*\d+', text.lower()) or \
           re.fullmatch(r'fig\.\s*\d+', text.lower()) or \
           re.fullmatch(r'table\s+\d+', text.lower()):
            continue
        digit_count = sum(1 for c in text if c.isdigit())
        if digit_count > len(text) * 0.5:
            continue
        if all(not c.isalnum() for c in text):
            continue
        if text.endswith('.') and not is_heading_pattern(text):
            continue
        if len(text) > 150:
            continue
        if sum(1 for c in text if c.islower()) > len(text) * 0.8 and not is_heading_pattern(text):
            continue
        if any(pattern in text.lower() for pattern in [
            'this is', 'there are', 'it is', 'they are', 'we can', 'you can',
            'the following', 'as follows', 'for example', 'such as'
        ]):
            continue
        filtered.append(heading)
    return filtered

def apply_post_processing_filters(headings, allow_common_section_duplicates=True, custom_common_sections=None):
    headings = merge_split_headings(headings)
    headings = remove_duplicate_headings(headings, allow_common_section_duplicates, custom_common_sections)
    headings = validate_heading_hierarchy(headings)
    headings = filter_invalid_headings(headings)
    return headings 