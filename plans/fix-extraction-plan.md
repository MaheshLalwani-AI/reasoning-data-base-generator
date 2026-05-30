# Fix Plan: PDF Extraction Pipeline

## Root Causes Identified

### Problem 1: Parser misses questions from many PDFs
- [`PlainMCQParser`](src/extraction/parsers/plain_mcq_parser.py:8-10) only matches `Q.\d+` (questions prefixed with "Q.")
- [`ParserRouter`](src/extraction/parser_router.py:63-66) correctly detects plain-numbered MCQs via `\n\s*\d+\.` pattern
- But the parser itself cannot extract those questions because it only looks for `Q.` prefix
- PDFs with `1.`, `2.`, `3.` numbering produce 0 questions despite being detected as plain-MCQ format

### Problem 2: Non-reasoning questions leak through
- [`NEGATIVE_KEYWORDS`](src/classification/regex_classifier.py:603-656) is missing many GK/maths/English/Computer keywords
- Positive reasoning keywords like "number", "letter", "word", "floor", "age" are too generic

### Problem 3: LLM Classifier needs to be disconnected
- Currently [`main.py`](src/main.py:5-8) imports and uses both `RegexClassifier` and `LLMClassifier`
- User wants to remove LLM from pipeline but keep the file for later

## Fix Steps

### Step 1: Disconnect LLM Classifier from `src/main.py`
- Remove `LLMClassifier` import
- Simplify `classify_questions()` to only use `RegexClassifier`
- Remove `llm_clf` parameter from `process_pdf()` and `main()`
- Remove LLM-related output from Excel writing path

### Step 2: Fix `PlainMCQParser` to handle plain `\d+.` numbering
- Add a second `QUESTION_PATTERN_PLAIN` for `^\d+\.` at start of lines
- In `parse_pages()`, try both patterns (Q-prefixed first, then plain)
- Add `QUESTION_NUMBER_PATTERN_PLAIN` to extract number from `1.` format
- Use `re.MULTILINE` flag so `^` matches line starts
- Validate: skip lines that look like option numbers (e.g., after option text)

### Step 3: Expand `NEGATIVE_KEYWORDS` in `RegexClassifier`
- Add more GK terms: "largest", "capital of", "amendment", "article", "chief minister", etc.
- Add more English terms: "comprehension", "synonyms of", "plural", "noun", etc.
- Add more Maths terms: "cost price", "selling price", "area of", "volume of", "radius", etc.
- Add Computer Awareness terms: "cpu", "ram", "operating system", etc.

### Step 4: Update `ExcelWriter` headers
- Remove "LLM Topic" from headers

### Step 5: Update `models.py`
- Remove `llm_topic` field from `Question` dataclass (optional, can leave unused)

## Execution Order
1. `src/models.py` - Remove `llm_topic` 
2. `src/extraction/parsers/plain_mcq_parser.py` - Add plain numbering support
3. `src/classification/regex_classifier.py` - Expand negative keywords
4. `src/main.py` - Disconnect LLM, simplify pipeline
5. `src/extraction/excel_writer.py` - Remove LLM column
