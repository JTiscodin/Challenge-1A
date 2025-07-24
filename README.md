# Challenge 1A PDF Heading Extractor

This project processes PDF files to extract document titles and a structured outline of headings (H1, H2, H3) using advanced heuristics and clustering. The extracted data is saved as JSON files for each PDF.

## Features
- Detects headings using font size, boldness, alignment, and content patterns
- Handles uniform and non-uniform font documents
- Removes duplicate and invalid headings
- Outputs a clean JSON outline per PDF

## Directory Structure
- `src/` - Contains all modularized Python code
- `PDFs/` - Input directory for PDF files
- `PDFs_output_new/` - Output directory for JSON results
- `main.py` - (Legacy) Monolithic script (now modularized)

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Place your PDF files in the `PDFs/` directory.
3. Run the main script:
   ```bash
   python -m src.main
   ```

## Requirements
- Python 3.7+
- See `requirements.txt` for dependencies

## Usage
- Outputs JSON files for each PDF in `PDFs_output_new/`.

## License
MIT License 