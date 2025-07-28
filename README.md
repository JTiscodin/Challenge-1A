# Challenge 1A PDF Heading Extractor

This project processes PDF files to extract document titles and a structured outline of headings (H1, H2, H3) using advanced heuristics and clustering. The extracted data is saved as JSON files for each PDF.

## Features
- Detects headings using font size, boldness, alignment, and content patterns
- Handles uniform and non-uniform font documents
- Removes duplicate and invalid headings
- **Multilingual Support**: Processes PDFs in multiple languages including English, Spanish, French, German, Italian, Portuguese, and more
- Outputs a clean JSON outline per PDF

## Directory Structure
- `src/` - Contains all modularized Python code
- `input/` - Input directory for PDF files
- `output/` - Output directory for JSON results
- `main.py` - (Legacy) Monolithic script (now modularized)

## Setup

### Local Development
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Place your PDF files in the `input/` directory.
3. Run the local script:
   ```bash
   python local_entrypoint.py
   ```

### Docker Deployment
1. Build the Docker image:
   ```bash
   docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .
   ```

2. Run the container:
   ```bash
   docker run --rm \
     -v "$(pwd -W)/input:/app/input" \
     -v "$(pwd -W)/output:/app/output" \
     --network none \
     mysolutionname:somerandomidentifier
   ```

## Requirements
- Python 3.7+
- See `requirements.txt` for dependencies
- Docker (for containerized deployment)

## Usage
- Outputs JSON files for each PDF in `output/` directory.
- Each JSON file contains:
  - `title`: Document title
  - `outline`: Array of headings with level (H1, H2, H3), text, and page number

## Output Format
```json
{
    "title": "Document Title",
    "outline": [
        {
            "level": "H1",
            "text": "Main Heading",
            "page": 1
        },
        {
            "level": "H2", 
            "text": "Subheading",
            "page": 2
        }
    ]
}
```

## License
MIT License 