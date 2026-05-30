# Comprehensive Fix Plan: All PDF Extraction Issues

## Root Cause Analysis

After analyzing the extracted Excel output and the codebase, here is a mapping of each issue to its root cause:

| Issue # | Description | Root Cause | File(s) to Fix |
|---------|-------------|------------|----------------|
| 1, 2, 3, 10 | Missing options (only 2-3 of 4 extracted) | `OPTION_PATTERN` regex lookahead boundary is too strict — it only stops at `Question ID`, `Chosen Option`, `Status`, or `\Z`. When options follow a different pattern (e.g., next question number, `Correct Option`, or no stop marker at all), options get silently dropped. | [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:87-109) |
| 4, 9 | Truncated question text mid-sentence | `QUESTION_PATTERN`, `QUESTION_PATTERN_QUE` split boundaries use lookahead for `Q.\d+` or `Que.\d+`, but if the text between questions has malformed spacing or line breaks, the regex fails to capture everything. Also, questions that span page boundaries lose trailing text. | [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:9-54) |
| 5 | OCR corruption in options (merged symbols and text) | No post-processing to clean common OCR artifacts like mathematical symbols merged with text, stray punctuation around option values. | [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:450-487) |
| 6 | Malayalam script garbled (`yLoPf]q]pOoLp]`) | The PDF text extraction via PyMuPDF (`fitz`) extracts Malayalam text using a non-Unicode-compatible encoding. These are non-recoverable artifacts from the PDF itself. The fix is to detect and filter out garbled non-English text with low Unicode ratio. | [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:450-487) |
| 7 | Non-reasoning questions (GK, English grammar) leak through | `NEGATIVE_KEYWORDS` in `RegexClassifier` is missing many English grammar terms (e.g., "error detection", "substitute", "sentence improvement") and GK terms (e.g., "who was", "famous folk music", "isotopes", "nuclear power"). | [`regex_classifier.py`](src/classification/regex_classifier.py:603-745) |
| 8 | Page numbers bleeding into options ("Page - 5", "Page - 11") | No cleanup for "Page - N" artifacts in `_clean_text` or option extraction. | [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:450-487) |
| 11 | 5th option column missing | Models and ExcelWriter hardcode 4 option columns. Need to support up to 5 options and add Option 5 column in the Excel output. | [`models.py`](src/models.py:19-21), [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:436), [`excel_writer.py`](src/extraction/excel_writer.py:11-26) |
| 12 | "Que. 2", ")" prefix in question/option text | `QUESTION_NUMBER_PATTERN_QUE` extracts the number but the "Que. N" text is NOT removed from question text. In `_clean_text`, the "Que." prefix is not stripped. Also, option text from `ibps-rrb-po` PDFs has closing `)` that should be removed. | [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:396-430) |

## Fix Plan: Step-by-Step

### Step 1: Expand `OPTION_PATTERN` lookahead in [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:87-109)

**Problem:** Missing options (Issues 1, 2, 3, 10).

The current `OPTION_PATTERN` only recognizes these stop markers:
- `(?:Ans\s*)?\d+\.` (next numbered option)
- `Question\s*ID`
- `Chosen\s*Option`
- `Status`
- `\Z`

But the actual text often has:
- `Correct\s*Option` section
- `Correct\s*Answer` section
- `^\s*\d+\.\s+\d+` (next question number) — e.g., "6. Which of the following..."
- `^\s*Que\.\s*\d+` (next "Que." question)

**Fix:** Add these stop markers to the lookahead:

```python
OPTION_PATTERN = re.compile(
    r"""
    (?:
        Ans\s*
    )?
    (\d+)\.
    \s*
    (.*?)
    (?=
        (?:Ans\s*)?\d+\.
        |
        Question\s*ID
        |
        Chosen\s*Option
        |
        Status
        |
        Correct\s*Option          # NEW
        |
        Correct\s*Answer          # NEW
        |
        ^\s*\d+\.\s+\d+           # NEW: next question number
        |
        ^\s*Que\.\s*\d+           # NEW: next Que. question
        |
        Page\s*-\s*\d+            # NEW: page marker
        |
        \Z
    )
    """,
    re.DOTALL | re.VERBOSE | re.MULTILINE,
)
```

Also add `Correct\s*Option` and `Correct\s*Answer` as stop markers to `LETTER_OPTION_PATTERN` and `PAREN_DIGIT_OPTION_PATTERN`.

### Step 2: Expand question boundary patterns in [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:9-54)

**Problem:** Question text truncation (Issues 4, 9).

**Fix:** Add `Correct\s*Option` and `Correct\s*Answer` as additional stop markers in the lookahead for all three question patterns, so they don't consume answer key text.

For `QUESTION_PATTERN`:
```python
QUESTION_PATTERN = re.compile(
    r"""
    (
        Q\.\d+.*?
    )
    (?=
        Q\.\d+
        |
        Correct\s*Option      # NEW
        |
        Correct\s*Answer      # NEW
        |
        \Z
    )
    """,
    re.DOTALL | re.VERBOSE,
)
```

Similarly for `QUESTION_PATTERN_PLAIN` and `QUESTION_PATTERN_QUE`.

### Step 3: Add cross-page question merging in [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:153-262)

**Problem:** Questions split across pages lose trailing text/options (Issues 4, 9).

Current logic processes each page independently. If a question starts on page N and ends on page N+1, both halves are incomplete.

**Fix:** Add a carry-over mechanism:

```python
def parse_pages(self, pages):
    questions = []
    carry_over = ""  # Text that was incomplete on previous page
    
    for page in pages:
        page_text = self._get_page_text(page)
        
        # Prepend carried-over text if any
        if carry_over:
            page_text = carry_over + "\n" + page_text
            carry_over = ""
        
        # Extract questions...
        matches = self._extract_question_chunks(page_text)
        
        for match in matches:
            # ... parse each question ...
        
        # Check if the last chunk is incomplete (no options found)
        if matches:
            last_chunk = matches[-1].group(1).strip()
            # Quick heuristic: if chunk doesn't end with an option number
            # or explicit stop marker, it likely continues to next page
            if not self._chunk_is_complete(last_chunk):
                carry_over = last_chunk
                # Remove the incomplete question from results
                if questions and not questions[-1].options:
                    questions.pop()
    
    return questions
```

Add a helper:
```python
def _chunk_is_complete(self, chunk):
    """Check if a question chunk appears complete (has options)."""
    # A complete chunk should end with an option, answer key, etc.
    return bool(
        re.search(r'(?:Correct\s*Option|Correct\s*Answer|Status)', chunk)
        or len(self.OPTION_PATTERN.findall(chunk)) >= 2
    )
```

### Step 4: Remove "Que. N" and ")" artifacts from extracted text in [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py)

**Problem:** Issue 12 — "Que. 2" and ")" leak into question and option text.

Looking at the IBPS RRB PO data (rows 1242-1315), the text has:
```
Que. 2
How is H related to J?
) Uncle
) Father
```

The question text gets "Que. 2" embedded, and options get leading ")".

**Fix:**

1. In `_parse_question`, after matching and before extracting text, remove the "Que. N" or "Q.N" label from the chunk:

```python
# After extracting chunk, remove question number prefix
if qno_match:
    chunk = self.QUESTION_NUMBER_PATTERN_QUE.sub("", chunk, count=1)
    chunk = self.QUESTION_NUMBER_PATTERN.sub("", chunk, count=1)
    chunk = self.QUESTION_NUMBER_PATTERN_PLAIN.sub("", chunk, count=1)
```

2. In `_clean_text`, add a cleanup rule for leading `)` in option text:

```python
# Remove leading ")" or ") " from option text
line = re.sub(r'^\)\s*', '', line).strip()
```

### Step 5: Add garbled text filter and page number cleanup in [`plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py:450-487)

**Problem:** OCR corruption (Issue 5), page numbers (Issue 8), garbled text (Issue 6).

**Fix:** Extend `_clean_text` with:

```python
def _clean_text(self, text):
    lines = []
    for line in text.splitlines():
        # existing: strip whitespace and Unicode noise
        line = line.strip().strip('\xa0\ufeff\u200b')
        if not line:
            continue

        lower = line.lower()
        if "adda247" in lower or "exammix" in lower:
            continue

        # Remove artifacts
        line = re.sub(r"(?i)\bAns\s*\d*\b", "", line).strip()
        line = re.sub(r"(?i)[\s\.]+[xX]\s*$", "", line).strip()

        # NEW: Remove "Page - N" artifacts
        line = re.sub(r'\bPage\s*-\s*\d+\b', '', line).strip()

        # NEW: Remove leading ")" from option text
        line = re.sub(r'^\)\s*', '', line).strip()

        # Skip if residue line
        if not line or line.lower() in ('x', 'x.', '.x'):
            continue

        # NEW: Filter garbled non-English text
        if self._is_garbled_text(line):
            continue

        lines.append(line)
    
    return "\n".join(lines).strip()
```

Add new method:

```python
@staticmethod
def _is_garbled_text(text: str) -> bool:
    """Detect garbled/ corrupted non-English text from PDF extraction."""
    if not text:
        return False
    
    # Count characters that are valid English letters, digits, or common punctuation
    valid_chars = len(
        re.findall(
            r'[A-Za-z0-9\s\.\,\?\!\(\)\[\]\{\}\+\-\*\/\=\>\<\@\#\$\%\^\&\:\;\"\'\`\~\|\\]',
            text,
        )
    )
    total_chars = len(text.strip())
    
    if total_chars == 0:
        return False
    
    # If less than 40% are valid characters, it's likely garbled
    # Exempt very short text (may be valid math answers like "42°")
    if total_chars < 5:
        return False
    
    return (valid_chars / total_chars) < 0.4
```

### Step 6: Support 5 options in models, parser, and Excel writer

**Problem:** Issue 11 — 5th option column is missing.

**Fixes:**

1. **`plain_mcq_parser.py`** line 442: Change `options[:4]` to `options[:5]`

2. **`excel_writer.py`**: 
   - Add `"Option 5"` to `QUESTION_HEADERS` list
   - In `_write_questions_sheet`, change padding from `while len(options) < 4` to `while len(options) < 5`
   - Add `options[4]` to the row builder

### Step 7: Expand `NEGATIVE_KEYWORDS` in [`regex_classifier.py`](src/classification/regex_classifier.py:603-745)

**Problem:** Issue 7 — Non-reasoning questions leak through.

**Principle:** Only add **generic structural patterns** that would appear across any exam PDF, NOT question-specific terms (e.g., avoid "Swami Vivekananda", "Eknath Shinde", "Cyclostomata").

**English/Grammar additions** (these are structural patterns common to ALL English grammar questions):

```python
# English (Additional generic patterns)
"sentence", "error", "grammar",
"parts of the following sentence",
"substitute the underlined",
"select the most appropriate",
"underlined segment",
"contains an error",
"no error",
```

**GK/General Knowledge additions** (only generic structural patterns, no specific names):

```python
# GK (Additional generic patterns)
"in which year",
"who discovered",
"who invented",
"founded by",
"established in",
"known for",
"famous for",
"located in",
"refers to",
"is related to",
"is known as",
"was born",
"belongs to",
"is called",
```

**Rationale:** These generic GK terms like "in which year", "who discovered", "founded by" will match ANY GK/history question regardless of the specific subject matter, making them robust across all PDFs.

### Step 8: Separate question text from options when both use `\d+.`

**Problem:** Some questions contain numbers like "6." within the question text itself, which the `OPTION_PATTERN` would incorrectly grab as an option.

**Fix:** When removing options from question text, be smarter about it. Only remove option numbers that appear AFTER the question body is complete. The key insight is that options appear in a dense block near the end of the chunk.

No code change needed here — the current approach already handles this by pattern matching from the full chunk and then removing the matched option patterns from the chunk. However, to prevent false positives, add a filter that option patterns must start at the **beginning of a line**:

```python
OPTION_PATTERN = re.compile(
    r"""
    (?:
        Ans\s*
    )?
    ^\s*                    # Must be at start of a line (NEW)
    (\d+)\.
    \s*
    (.*?)
    (?= ... )
    """,
    re.DOTALL | re.VERBOSE | re.MULTILINE,
)
```

## Execution Order

The fixes should be implemented in this order to avoid cascading dependencies:

| Order | File | Changes | Issues Fixed |
|-------|------|---------|--------------|
| 1 | [`src/extraction/parsers/plain_mcq_parser.py`](src/extraction/parsers/plain_mcq_parser.py) | All parser-level fixes: expand OPTION_PATTERN lookahead, expand question boundaries, add cross-page merging, remove "Que. N"/")" artifacts, add garbled text filter, add Page-N cleanup, support 5 options | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12 |
| 2 | [`src/extraction/excel_writer.py`](src/extraction/excel_writer.py) | Add Option 5 column, handle up to 5 options | 11 |
| 3 | [`src/classification/regex_classifier.py`](src/classification/regex_classifier.py) | Expand NEGATIVE_KEYWORDS with generic structural patterns only | 7 |

## Testing Strategy

After implementing all fixes, run the pipeline on ALL PDFs:

```bash
cd /home/mahesh/reasoning_book/reasoning-pdf-parser
uv run python src/main.py
```

Verify against the generated Excel:
1. Rows 45, 63, 68, 72, 79 — complete questions and options
2. Rows 15-37 (Kerala PSC) — garbled text filtered out
3. Rows 270-273, 285-291 (SSC CHSL) — English/GK questions removed
4. Rows 259, 269 (IBPS RRB PO) — no "Page - N" in option text
5. Rows 53, 59, 77, 93 — no truncation ending with "allowe" or "wor"
6. IBPS RRB PO rows — no "Que. 2", ")" artifacts
7. Any questions with 5 options — correctly populated in Option 5 column
8. Extraction Report — improved parsed question counts and accuracy

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Expanding OPTION_PATTERN lookahead | Could over-capture leading into next question | Require option patterns to start at line beginning with `^` |
| Garbled text detection | Could filter genuine short English text | Exempt text under 5 characters; 40% threshold tuned to only catch extreme cases |
| Carrying text across pages | Could merge unrelated content | Only carry over if last chunk has no options found |
| Expanding NEGATIVE_KEYWORDS | Could falsely flag reasoning questions with incidental GK terms | Keywords are structural ("in which year", "who discovered") — reasoning questions rarely contain these patterns |
| Adding Option 5 column | Backward compatibility | New column appended; existing data unaffected |
