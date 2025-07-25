import os
import sys
from src.single_pdf import process_pdf

INPUT_DIR = 'input'
OUTPUT_DIR = 'output'

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    if not os.path.exists(INPUT_DIR):
        print(f"Input directory '{INPUT_DIR}' not found!")
        return
    
    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in '{INPUT_DIR}' directory!")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process:")
    for filename in pdf_files:
        pdf_path = os.path.join(INPUT_DIR, filename)
        output_filename = os.path.splitext(filename)[0] + '.json'
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        try:
            print(f"Processing {filename}...")
            process_pdf(pdf_path, output_path)
            print(f"✓ Successfully processed {filename} -> {output_filename}")
        except Exception as e:
            print(f"✗ Failed to process {filename}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main() 