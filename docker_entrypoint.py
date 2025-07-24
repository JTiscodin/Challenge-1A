import os
import sys
from src.single_pdf import process_pdf

INPUT_DIR = '/app/input'
OUTPUT_DIR = '/app/output'

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(INPUT_DIR, filename)
            output_filename = os.path.splitext(filename)[0] + '.json'
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            try:
                process_pdf(pdf_path, output_path)
                print(f"Processed {filename} -> {output_filename}")
            except Exception as e:
                print(f"Failed to process {filename}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main() 