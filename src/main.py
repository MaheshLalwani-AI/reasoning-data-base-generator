from pathlib import Path

from dotenv import load_dotenv

from classification import (
    LLMClassifier,
    RegexClassifier,
)

from extraction.answer_detector import AnswerDetector
from extraction.excel_writer import ExcelWriter
from extraction.extractor import PDFExtractor

from extraction.parsers.metadata_parser import (
    QuestionParser as MetadataParser,
)

from extraction.parsers.plain_mcq_parser import (
    QuestionParser as UniversalParser,
)


def get_pdf_paths() -> list[Path]:
    pdf_folder = Path("data/pdfs")

    pdf_files = sorted(
        pdf_folder.glob("*.pdf")
    )

    if not pdf_files:
        raise FileNotFoundError(
            "No PDFs found in data/pdfs"
        )

    return pdf_files


def choose_parser(pages):
    sample_text = ""

    for page in pages[:3]:
        blocks = page.get("blocks", [])

        for block in blocks:
            sample_text += (
                block.get("text", "")
                + "\n"
            )

    if (
        "Question Number" in sample_text
        and "Question Id" in sample_text
    ):
        print("Using metadata parser")
        return MetadataParser()

    print("Using universal parser")
    return UniversalParser()


def apply_detected_answers(
    questions,
    answers: dict[tuple[int, int], str],
) -> int:
    applied_count = 0

    for question in questions:
        key = (
            question.page_number,
            question.question_number,
        )

        if key not in answers:
            continue

        try:
            option_number = int(answers[key])
            option_index = option_number - 1

            if 0 <= option_index < len(question.options):
                question.correct_answer = (
                    question.options[option_index]
                )
                applied_count += 1

        except Exception:
            continue

    return applied_count


def classify_questions(
    questions,
    regex_clf: RegexClassifier,
    llm_clf: LLMClassifier,
):
    filtered = []

    for question in questions:
        text_for_clf = (
            question.question_text
            + "\n"
            + "\n".join(question.options)
        )

        regex_result = regex_clf.classify(
            text_for_clf
        )

        question.regex_topic = (
            regex_result["regex_topic"]
        )

        if regex_result["negative_hits"] > 0:
            question.is_reasoning = False
            continue

        llm_result = llm_clf.classify(
            text_for_clf
        )

        llm_says = llm_result["is_reasoning"]

        if llm_says is None:
            question.is_reasoning = (
                regex_result["is_reasoning_hint"]
            )
            question.llm_topic = ""
        else:
            question.is_reasoning = llm_says
            question.llm_topic = (
                llm_result["llm_topic"]
            )

        if not question.is_reasoning:
            continue

        filtered.append(question)

    return filtered


def build_report_row(
    pdf_name: str,
    pages_count: int,
    parsed_count: int,
    detected_answers_count: int,
    applied_answers_count: int,
    kept_count: int,
) -> dict:
    missing_answers_count = max(
        parsed_count - applied_answers_count,
        0,
    )

    if parsed_count:
        answer_coverage = round(
            applied_answers_count / parsed_count * 100,
            2,
        )
    else:
        answer_coverage = 0.0

    return {
        "pdf_name": pdf_name,
        "pages_count": pages_count,
        "parsed_questions": parsed_count,
        "detected_answer_keys": detected_answers_count,
        "applied_answers": applied_answers_count,
        "missing_answers": missing_answers_count,
        "answer_coverage_percent": answer_coverage,
        "reasoning_questions_kept": kept_count,
    }


def process_pdf(
    pdf_path: Path,
    regex_clf: RegexClassifier,
    llm_clf: LLMClassifier,
):
    print("\n=======================")
    print(f"PROCESSING: {pdf_path.name}")
    print("=======================\n")

    print("[1] Extracting PDF...")

    extractor = PDFExtractor(
        pdf_path=str(pdf_path)
    )

    pages = extractor.extract_pages()

    print(
        f"Pages extracted: {len(pages)}\n"
    )

    print("[2] Parsing questions...")

    parser = choose_parser(pages)
    questions = parser.parse_pages(pages)

    print(
        f"Questions parsed: {len(questions)}\n"
    )

    exam_name = pdf_path.stem

    for question in questions:
        question.exam_name = exam_name

    print("[3] Detecting answers...")

    detector = AnswerDetector(
        pdf_path=str(pdf_path)
    )

    answers = detector.detect_answers()

    print(
        f"Answer keys detected: {len(answers)}"
    )

    applied_answers_count = apply_detected_answers(
        questions=questions,
        answers=answers,
    )

    print(
        f"Answers applied to parsed questions: "
        f"{applied_answers_count}\n"
    )

    print("[4] Classifying questions...")

    filtered = classify_questions(
        questions=questions,
        regex_clf=regex_clf,
        llm_clf=llm_clf,
    )

    print(
        f"Reasoning questions kept: "
        f"{len(filtered)} / {len(questions)}\n"
    )

    report_row = build_report_row(
        pdf_name=pdf_path.name,
        pages_count=len(pages),
        parsed_count=len(questions),
        detected_answers_count=len(answers),
        applied_answers_count=applied_answers_count,
        kept_count=len(filtered),
    )

    return filtered, report_row


def main():
    load_dotenv()

    pdf_paths = get_pdf_paths()

    print(
        f"\nPDFs found: {len(pdf_paths)}\n"
    )

    regex_clf = RegexClassifier()
    llm_clf = LLMClassifier()

    if llm_clf.enabled:
        print(
            "LLM classifier: ENABLED "
            f"({llm_clf.model})\n"
        )
    else:
        print(
            "LLM classifier: disabled "
            "(no OPENROUTER_API_KEY)\n"
        )

    all_questions = []
    report_rows = []

    for pdf_path in pdf_paths:
        try:
            questions, report_row = process_pdf(
                pdf_path=pdf_path,
                regex_clf=regex_clf,
                llm_clf=llm_clf,
            )

            all_questions.extend(questions)
            report_rows.append(report_row)

        except Exception as e:
            print(
                f"\nFAILED: {pdf_path.name}"
            )
            print(e)

            report_rows.append(
                {
                    "pdf_name": pdf_path.name,
                    "pages_count": 0,
                    "parsed_questions": 0,
                    "detected_answer_keys": 0,
                    "applied_answers": 0,
                    "missing_answers": 0,
                    "answer_coverage_percent": 0.0,
                    "reasoning_questions_kept": 0,
                    "error": str(e),
                }
            )

    output_path = Path(
        "data/extracted/extracted_questions.xlsx"
    )

    print("\n[5] Writing Excel...")

    writer = ExcelWriter()

    writer.write(
        questions=all_questions,
        output_path=str(output_path),
        report_rows=report_rows,
    )

    total_questions = sum(
        row.get("parsed_questions", 0)
        for row in report_rows
    )

    total_applied_answers = sum(
        row.get("applied_answers", 0)
        for row in report_rows
    )

    total_missing_answers = sum(
        row.get("missing_answers", 0)
        for row in report_rows
    )

    print("\n=======================")
    print("EXCEL GENERATED")
    print(f"Output: {output_path}")
    print("-----------------------")
    print(f"Total parsed questions: {total_questions}")
    print(f"Total applied answers: {total_applied_answers}")
    print(f"Total missing answers: {total_missing_answers}")
    print("=======================\n")


if __name__ == "__main__":
    main()