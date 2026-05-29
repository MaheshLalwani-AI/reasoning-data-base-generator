# Reasoning Database Generator

This project extracts reasoning questions from exam PDF files and generates an Excel dataset.

## What it does

- Reads PDFs from `data/pdfs`
- Parses questions and options
- Detects correct answers from the PDF
- Classifies reasoning questions
- Writes an Excel file to `data/extracted/extracted_questions.xlsx`
- Writes an extraction report sheet inside the Excel file

## Folder structure
text
data/
pdfs/
input PDFs go here

extracted/
extracted_questions.xlsx is generated here

cache/
LLM classification cache is stored here

src/
main.py
models.py

extraction/
answer_detector.py
excel_writer.py
extractor.py
parsers/

classification/
regex_classifier.py
llm_classifier.py
topics_loader.py

## Setup

Install dependencies:
bash
uv sync
If you are not using `uv`, install the dependencies from `pyproject.toml` using your preferred Python tool.

## Environment variables

Create a `.env` file if you want LLM classification.
env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=deepseek/deepseek-chat

If `OPENROUTER_API_KEY` is missing, the project will still run. It will fall back to regex classification where possible.

## Input

Put PDF files here:
text
data/pdfs/

bash
uv run python src/main.py

code



bash
python src/main.py

code


## Output

The generated Excel file will be created at:
text
data/extracted/extracted_questions.xlsx

code


The Excel file contains:

1. `Questions`
2. `Extraction Report`

## Notes

Image extraction is currently disconnected from the pipeline.

This keeps the extraction flow focused on text, options, correct answers, and reasoning classification. Image handling can be added back later as a separate step.