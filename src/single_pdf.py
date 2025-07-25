import os
import json
import fitz
import re
import numpy as np
from sklearn.cluster import KMeans
from collections import Counter

INPUT_DIR = os.path.join(os.path.dirname(__file__), 'input')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output_new')

HEADING_LEVELS = ['H1', 'H2', 'H3']

# Regex for heading patterns (e.g., 1., 1.1, 2.3.4, I., A., etc.)
HEADING_PATTERNS = [
    re.compile(r'^(\d+\.)+\s+'),
    re.compile(r'^[A-Z]\.\s+'),
    re.compile(r'^[IVXLCDM]+\.\s+', re.IGNORECASE),
    re.compile(r'^[A-Z][A-Z\s\-]+$'),  # ALL CAPS
]

def is_heading_pattern(text):
    for pat in HEADING_PATTERNS:
        if pat.match(text):
            return True
    return False

def extract_title(page):
    # Only consider the largest, centered, short text (<=5 words) in the top 25% of the first page as the title
    blocks = page.get_text("dict")['blocks']
    spans = []
    page_height = page.rect.height
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
                        'bold': (span['flags'] & 2 != 0)
                    })
    if not spans:
        return ""
    max_size = max(s['size'] for s in spans)
    # Only consider text in the top 25% of the page
    top_spans = [s for s in spans if s['y0'] < page_height * 0.25 and abs(s['size'] - max_size) < 1.0]
    # Prefer centered and short (<=5 words)
    centered_spans = [s for s in top_spans if abs((s['x0'] + s['x1'])/2 - page.rect.width/2) < 100 and len(s['text'].split()) <= 5]
    if centered_spans:
        centered_spans.sort(key=lambda s: s['y0'])
        return centered_spans[0]['text']
    # Otherwise, pick the largest, shortest line
    short_spans = [s for s in top_spans if len(s['text'].split()) <= 5]
    if short_spans:
        short_spans.sort(key=lambda s: s['y0'])
        return short_spans[0]['text']
    # Fallback: pick the first largest line in the top 25%
    if top_spans:
        top_spans.sort(key=lambda s: s['y0'])
        return top_spans[0]['text']
    # Last fallback: largest line anywhere
    largest_spans = [s for s in spans if abs(s['size'] - max_size) < 1.0]
    largest_spans.sort(key=lambda s: s['y0'])
    return largest_spans[0]['text'] if largest_spans else spans[0]['text']

def cluster_font_sizes(sizes):
    # Use KMeans to cluster font sizes into 3 groups (H1, H2, H3)
    arr = np.array(sizes).reshape(-1, 1)
    n_clusters = min(3, len(set(sizes)))
    if n_clusters < 2:
        return {"H1": max(sizes), "H2": min(sizes), "H3": min(sizes)}
    kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(arr)
    centers = sorted([c[0] for c in kmeans.cluster_centers_], reverse=True)
    thresholds = {"H1": centers[0], "H2": centers[1] if n_clusters > 1 else centers[0], "H3": centers[2] if n_clusters > 2 else centers[-1]}
    return thresholds

def detect_headings(page, thresholds, header_footer_texts=None):
    headings = []
    blocks = page.get_text("dict")['blocks']
    page_width = page.rect.width
    for block in blocks:
        for line in block.get('lines', []):
            for span in line['spans']:
                text = span['text'].strip()
                if not text or len(text) < 2:
                    continue
                # Filter out headers/footers
                if header_footer_texts and text in header_footer_texts:
                    continue
                size = span['size']
                flags = span['flags']
                is_bold = flags & 2 != 0
                x0 = span['bbox'][0]
                x1 = span['bbox'][2]
                y0 = span['bbox'][1]
                y1 = span['bbox'][3]
                
                # Only allow left-aligned (x0 < 120) or centered
                is_left_aligned = x0 < 120
                is_centered = abs((x0 + x1)/2 - page_width/2) < 100
                if not (is_left_aligned or is_centered):
                    continue
                # Only consider as heading if (a) font size > 13pt, or (b) matches heading pattern
                level = None
                if size > 13:
                    if size >= thresholds['H1'] - 0.5:
                        level = 'H1'
                    elif size >= thresholds['H2'] - 0.5:
                        level = 'H2'
                    elif size >= thresholds['H3'] - 0.5:
                        level = 'H3'
                elif is_heading_pattern(text):
                    if size >= thresholds['H2'] - 1.5:
                        level = 'H2'
                    else:
                        level = 'H3'
                if not level:
                    continue
                # Filter out lines that are too long (>10 words) or too short (<2 words), unless matches heading pattern
                word_count = len(text.split())
                if (word_count > 10 or word_count < 2) and not is_heading_pattern(text):
                    continue
                # Ignore lines that are mostly lowercase (unless heading pattern)
                if not is_heading_pattern(text) and sum(1 for c in text if c.isupper()) < 2:
                    continue
                
                headings.append({
                    'level': level, 
                    'text': text, 
                    'page': page.number + 1,
                    'y0': y0,
                    'y1': y1,
                    'x0': x0,
                    'x1': x1,
                    'size': size
                })
    return headings

def get_header_footer_texts(doc):
    # Find repeated text at the top/bottom of every page (likely header/footer)
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
    # Most common top/bottom texts
    header = [t for t, c in Counter(top_texts).items() if c > len(doc) // 2]
    footer = [t for t, c in Counter(bottom_texts).items() if c > len(doc) // 2]
    return set(header + footer)

def merge_split_headings(headings):
    """
    Filter 1: Merge headings that are likely parts of the same logical heading
    (same page, same level, close vertical proximity)
    """
    if not headings:
        return headings
    
    # Sort by page, then by y-coordinate
    sorted_headings = sorted(headings, key=lambda h: (h['page'], h['y0']))
    merged = []
    
    i = 0
    while i < len(sorted_headings):
        current = sorted_headings[i]
        merged_text = current['text']
        
        # Look ahead for potential continuations
        j = i + 1
        while j < len(sorted_headings):
            next_heading = sorted_headings[j]
            
            # Check if this could be a continuation:
            # 1. Same page and level
            # 2. Close vertical proximity (within 30 pixels)
            # 3. Current text doesn't end with punctuation (suggesting continuation)
            if (next_heading['page'] == current['page'] and 
                next_heading['level'] == current['level'] and
                abs(next_heading['y0'] - current['y1']) < 30 and
                not current['text'].rstrip().endswith(('.', '!', '?', ':'))):
                
                # Merge the texts
                merged_text += " " + next_heading['text']
                current['y1'] = next_heading['y1']  # Update bottom coordinate
                current['x1'] = max(current['x1'], next_heading['x1'])  # Update right coordinate
                j += 1
            else:
                break
        
        # Create merged heading
        merged_heading = current.copy()
        merged_heading['text'] = merged_text.strip()
        merged.append(merged_heading)
        
        i = j
    
    return merged

def remove_duplicate_headings(headings):
    """
    Filter 2: Remove duplicate headings based on text similarity and proximity
    """
    if not headings:
        return headings
    
    unique_headings = []
    seen_texts = set()
    
    for heading in headings:
        text_norm = heading['text'].strip().lower()
        
        # Skip if we've seen this exact text before
        if text_norm in seen_texts:
            continue
            
        # Check for very similar texts (fuzzy matching)
        is_duplicate = False
        for existing_text in seen_texts:
            # Simple similarity check: if one text is contained in another and they're similar length
            if (text_norm in existing_text or existing_text in text_norm) and \
               abs(len(text_norm) - len(existing_text)) < 10:
                is_duplicate = True
                break
        
        if not is_duplicate:
            seen_texts.add(text_norm)
            unique_headings.append(heading)
    
    return unique_headings

def validate_heading_hierarchy(headings):
    """
    Filter 3: Validate and fix heading hierarchy issues
    """
    if not headings:
        return headings
    
    # Sort by page, then by y-coordinate
    sorted_headings = sorted(headings, key=lambda h: (h['page'], h['y0']))
    validated = []
    
    level_order = {'H1': 1, 'H2': 2, 'H3': 3}
    last_level = 0
    
    for heading in sorted_headings:
        current_level = level_order[heading['level']]
        
        # If we jump more than one level (e.g., H1 to H3), 
        # demote the current heading to maintain hierarchy
        if current_level > last_level + 1:
            if last_level == 1:
                heading['level'] = 'H2'
            elif last_level == 2:
                heading['level'] = 'H3'
            else:
                heading['level'] = 'H2'  # Default fallback
        
        validated.append(heading)
        last_level = level_order[heading['level']]
    
    return validated

def filter_invalid_headings(headings):
    """
    Filter 4: Remove headings that are likely false positives
    """
    if not headings:
        return headings
    
    filtered = []
    
    for heading in headings:
        text = heading['text'].strip()
        
        # Skip headings that are just numbers, single letters, or very short
        if re.fullmatch(r'[ivxlcdm]+\.?', text.lower()) or \
           re.fullmatch(r'\(?[ivxlcdm]+\)?\.?', text.lower()) or \
           re.fullmatch(r'\(?\d+\)?\.?', text) or \
           len(text) < 3:
            continue
        
        # Skip headings that are likely page numbers or references
        if re.fullmatch(r'page\s+\d+', text.lower()) or \
           re.fullmatch(r'p\.\s*\d+', text.lower()) or \
           re.fullmatch(r'fig\.\s*\d+', text.lower()) or \
           re.fullmatch(r'table\s+\d+', text.lower()):
            continue
        
        # Skip headings with too many numbers (likely references or codes)
        digit_count = sum(1 for c in text if c.isdigit())
        if digit_count > len(text) * 0.5:
            continue
        
        # Skip headings that are all punctuation
        if all(not c.isalnum() for c in text):
            continue
        
        filtered.append(heading)
    
    return filtered

def apply_post_processing_filters(headings):
    """
    Apply all post-processing filters in sequence
    """
    print(f"Initial headings: {len(headings)}")
    
    # Filter 1: Merge split headings
    headings = merge_split_headings(headings)
    print(f"After merging split headings: {len(headings)}")
    
    # Filter 2: Remove duplicates
    headings = remove_duplicate_headings(headings)
    print(f"After removing duplicates: {len(headings)}")
    
    # Filter 3: Validate hierarchy
    headings = validate_heading_hierarchy(headings)
    print(f"After validating hierarchy: {len(headings)}")
    
    # Filter 4: Remove invalid headings
    headings = filter_invalid_headings(headings)
    print(f"After filtering invalid headings: {len(headings)}")
    
    return headings

def process_pdf(pdf_path, output_path):
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
    
    # Title extraction
    title = extract_title(doc[0]) if len(doc) > 0 else ""
    
    # Extract headings from all pages
    outline = []
    for page in doc:
        headings = detect_headings(page, thresholds, header_footer_texts)
        outline.extend(headings)
    
    # Apply post-processing filters
    outline = apply_post_processing_filters(outline)
    
    # Sort final results by heading level, then by page, then by y-coordinate
    level_order = {'H1': 0, 'H2': 1, 'H3': 2}
    outline.sort(key=lambda h: (level_order.get(h['level'], 99), h['page'], h['y0']))
    
    # Clean up the output - remove coordinate info for final JSON
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