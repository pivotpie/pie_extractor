# Document Extractor CLI

A command-line interface for extracting text and structure from documents using OpenRouter's vision models.

## Features

- Extract text and structure from document images
- Process single files or entire directories
- Save results in JSON format
- Support for multiple image formats (PNG, JPG, JPEG, TIFF)
- Configurable model parameters

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/document-extractor.git
   cd document-extractor
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements-cli.txt
   ```

3. Set up your OpenRouter API key:
   - Create a `.env` file in the project root
   - Add your API key:
     ```
     OPENROUTER_API_KEY=your_api_key_here
     ```

## Usage

### Process a Single Document

```bash
python cli.py path/to/document.jpg -o output.json
```

### Process All Documents in a Directory

```bash
python cli.py path/to/documents -o output_directory
```

### Command-line Options

```
positional arguments:
  input                 Input file or directory

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file or directory (default: output.json or output_dir/)
  --api-key API_KEY     OpenRouter API key (default: from OPENROUTER_API_KEY environment variable)
  --model MODEL         Model to use for processing (default: meta-llama/llama-3.2-11b-vision-instruct:free)
  --max-tokens MAX_TOKENS
                        Maximum tokens for the API response (default: 4000)
  --temperature TEMPERATURE
                        Temperature for model sampling (0.0-2.0) (default: 0.1)
  --debug               Enable debug logging
```

## Output Format

The tool outputs a JSON file containing the extracted text and metadata in the following format:

```json
[
  {
    "text": "Extracted text content",
    "bbox": {
      "x": 0,
      "y": 0,
      "width": 100,
      "height": 20
    },
    "type": "header|body|table_cell|footer|signature|date|amount|other",
    "confidence": 0.95,
    "font_properties": {
      "estimated_size": 12,
      "bold": false,
      "italic": false
    }
  }
]
```

## Examples

1. Process a single document with default settings:
   ```bash
   python cli.py invoice.jpg -o invoice_data.json
   ```

2. Process all images in a directory with custom model parameters:
   ```bash
   python cli.py ./documents -o ./output --model meta-llama/llama-3.2-11b-vision-instruct:free --max-tokens 8000 --temperature 0.2
   ```

3. Process a document with debug logging:
   ```bash
   python cli.py document.png -o output.json --debug
   ```

## Troubleshooting

- **API Key Errors**: Ensure your OpenRouter API key is set in the `.env` file or provided via the `--api-key` parameter.
- **Image Loading Issues**: Make sure the input images are in a supported format (PNG, JPG, JPEG, TIFF).
- **JSON Parsing Errors**: The tool includes robust error handling for parsing model responses. If you encounter issues, try running with `--debug` for more detailed error information.

## License

This project is licensed under the MIT License.
