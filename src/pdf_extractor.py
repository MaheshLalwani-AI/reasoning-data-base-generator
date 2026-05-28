"""
PDF -> reasoning-questions Excel extractor.

Output columns (in order):
    question, question_image, options, answer, regex_topic, llm_topic

- Skips non-English text blocks.
- Saves embedded images per page and attaches the filename when the
  question looks image-based (non-verbal reasoning).
- No question_id column.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Optional

import fitz  # PyMuPDF
import pandas as pd

from page_classifier import PageClassifier
from llm_classifier import LLMClassifier


IMAGE_BASED_TOPICS = {
    "Mirror Image", "Water Image", "Paper Folding", "Paper Cutting",
    "Embedded Figures", "Counting Figures", "Figure Series",
    "Figure Analogy", "Figure Classification", "Figure Matrix",
    "Pattern Completion", "Cube and Dice", "Cube Construction",
    "Venn Diagram",
}

# Splits text into individual questions. Tweak to your PDFs' numbering style.
QUESTION_SPLIT_RE = re.compile(
    r"(?:^|\n)\s*(?:Q(?:uestion)?\s*[\.\:\-]?\s*)?(\d{1,3})[\.\)]\s+",
    re.IGNORECASE,
)


def is_english_dominant(text: str, threshold: float = 0.7) -> bool:
    if not text:
        return False
    latin = sum(1 for c in text if "a" <= c.lower() <= "z")
    alpha = sum(1 for c in text if c.isalpha())
    if alpha == 0:
        return False
    return (latin / alpha) >= threshold


def extract_images_from_page(page, page_num: int, out_dir: Path) -> List[str]:
    """Save every image on a page; return list of saved filenames."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for img_index, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        try:
            base = page.parent.extract_image(xref)
            ext = base.get("ext", "png")
            filename = f"page{page_num+1}_img{img_index+1}.{ext}"
            (out_dir / filename).write_bytes(base["image"])
            saved.append(filename)
        except Exception as e:
            print(f"[image extract] page {page_num+1} img {img_index+1}: {e}")
    return saved


def split_into_questions(page_text: str) -> List[str]:
    """Split a page's text into individual question chunks by leading number."""
    # Find all match starts
    starts = [m.start() for m in QUESTION_SPLIT_RE.finditer("\n" + page_text)]
    if not starts:
        # Whole page treated as one chunk
        return [page_text.strip()] if page_text.strip() else []

    chunks = []
    text = "\n" + page_text
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        chunk = text[s:e].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def parse_options_and_answer(chunk: str) -> Dict[str, str]:
    """Very lightweight option/answer pull; adjust to your PDF style."""
    # Options like (a) ... (b) ... or 1. ... 2. ...
    opts = re.findall(r"\(([a-dA-D])\)\s*([^\n\(]+)", chunk)
    options_str = " | ".join(f"({k.lower()}) {v.strip()}" for k, v in opts)

    ans_match = re.search(r"\bans(?:wer)?[\s\.\:\-]+\(?([a-dA-D1-4])\)?", chunk, re.I)
    answer = ans_match.group(1).lower() if ans_match else ""

    # Question text = everything before "(a)" or "Ans"
    cut = re.split(r"\([aA]\)|\bans(?:wer)?[\s\.\:\-]+", chunk, maxsplit=1)
    question_text = cut[0].strip()
    # Strip leading number "12. " etc.
    question_text = re.sub(r"^\s*\d+[\.\)]\s*", "", question_text).strip()

    return {
        "question": question_text,
        "options": options_str,
        "answer": answer,
    }


def extract_reasoning_questions(pdf_path: str, output_xlsx: str,
                                images_dir: str = "extracted_images",
                                use_llm: bool = False,
                                openrouter_api_key: Optional[str] = None):
    pdf_path = Path(pdf_path)
    images_root = Path(images_dir) / pdf_path.stem

    regex_clf = PageClassifier()
    llm_clf = LLMClassifier(api_key=openrouter_api_key) if use_llm else None

    rows = []
    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(doc):
        page_text = page.get_text("text") or ""

        # English-only filter (skip pages dominated by Hindi/regional scripts)
        if not is_english_dominant(page_text):
            continue

        # Extract images once per page; assign on demand
        page_images = extract_images_from_page(page, page_num, images_root)
        image_pool = list(page_images)  # consume in order

        for chunk in split_into_questions(page_text):
            if not is_english_dominant(chunk):
                continue

            # Classify
            result = regex_clf.classify(chunk)
            if not result["is_reasoning"]:
                continue

            parsed = parse_options_and_answer(chunk)
            if not parsed["question"]:
                continue

            regex_topic = result["regex_topic"]

            # Image-based reasoning? assign next available page image
            question_image = ""
            if regex_topic in IMAGE_BASED_TOPICS and image_pool:
                question_image = image_pool.pop(0)

            # LLM topic (optional)
            llm_topic = ""
            if llm_clf is not None:
                llm_topic = llm_clf.classify(chunk)

            rows.append({
                "question": parsed["question"],
                "question_image": question_image,
                "options": parsed["options"],
                "answer": parsed["answer"],
                "regex_topic": regex_topic,
                "llm_topic": llm_topic,
            })

    doc.close()

    df = pd.DataFrame(rows, columns=[
        "question", "question_image", "options", "answer", "regex_topic", "llm_topic"
    ])
    df.to_excel(output_xlsx, index=False)
    print(f"[done] wrote {len(df)} reasoning questions -> {output_xlsx}")
    print(f"[images] saved to {images_root}")
    return df


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="Input PDF path")
    ap.add_argument("--out", default="reasoning_questions.xlsx", help="Output xlsx")
    ap.add_argument("--images-dir", default="extracted_images")
    ap.add_argument("--use-llm", action="store_true", help="Enable LLM topic column")
    ap.add_argument("--openrouter-key", default=None)
    args = ap.parse_args()

    extract_reasoning_questions(
        args.pdf,
        args.out,
        images_dir=args.images_dir,
        use_llm=args.use_llm,
        openrouter_api_key=args.openrouter_key,
    )