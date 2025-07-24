import os
from .single_pdf import process_pdf

INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'PDFs')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'PDFs_output_new')

def process_all_pdfs():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(INPUT_DIR, filename)
            output_filename = os.path.splitext(filename)[0] + '.json'
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            print(f"Processing {filename} ...")
            try:
                process_pdf(pdf_path, output_path)
                print(f"Output written to {output_filename}")
            except Exception as e:
                print(f"Failed to process {filename}: {e}") 