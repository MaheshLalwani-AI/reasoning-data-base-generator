from pathlib import Path

from src.extraction.extractor import (
    PDFExtractor,
)

from src.extraction.parser_router import (
    ParserRouter,
)

from src.extraction.answer_detector import (
    AnswerDetector,
)

from src.extraction.excel_writer import (
    ExcelWriter,
)


def get_pdf_paths() -> list[Path]:

    pdf_folder = Path(
        "data/pdfs"
    )

    pdf_files = list(
        pdf_folder.glob("*.pdf")
    )

    if not pdf_files:

        raise FileNotFoundError(
            "No PDFs found inside data/pdfs"
        )

    return pdf_files


def process_pdf(
    pdf_path: Path,
):

    print(
        "\n----------------------"
    )

    print(
        f"Processing: "
        f"{pdf_path.name}"
    )

    print(
        "----------------------"
    )

    # STEP 1
    # EXTRACT PDF

    print(
        "[1] Extracting PDF..."
    )

    extractor = PDFExtractor(
        pdf_path=str(pdf_path)
    )

    pages = extractor.extract_pages()

    print(
        f"Pages extracted: "
        f"{len(pages)}"
    )

    # =========================
    # DEBUG SECTION
    # =========================

    print(
        "\n========== DEBUG =========="
    )

    print(
        f"pages type: {type(pages)}"
    )

    if pages:

        print(
            f"first page type: "
            f"{type(pages[0])}"
        )

        print(
            "\nFIRST PAGE CONTENT:\n"
        )

        print(pages[0])

    print(
        "\n===========================\n"
    )

    # STEP 2
    # PARSE QUESTIONS

    print(
        "[2] Parsing questions..."
    )

    parser = ParserRouter()

    questions = parser.parse_pages(
        pages
    )

    print(
        f"Questions parsed: "
        f"{len(questions)}"
    )

    # DEBUG QUESTIONS

    if questions:

        print(
            "\nFIRST QUESTION:\n"
        )

        print(questions[0])

        print()

    # ATTACH EXAM NAME

    exam_name = pdf_path.stem

    for question in questions:

        question.exam_name = (
            exam_name
        )

    # STEP 3
    # DETECT ANSWERS

    print(
        "[3] Detecting answers..."
    )

    detector = AnswerDetector(
        pdf_path=str(pdf_path)
    )

    answers = detector.detect_answers()

    print(
        f"Answers detected: "
        f"{len(answers)}"
    )

    # MAP ANSWERS

    mapped_count = 0

    for question in questions:

        # Match using composite key (Page, Question Number)
        key = (
            question.page_number,
            question.question_number,
        )

        if key not in answers:
            continue

        try:

            option_number = int(
                answers[key]
            )

            option_index = (
                option_number - 1
            )

            if (
                0
                <= option_index
                < len(question.options)
            ):

                question.correct_answer = (
                    question.options[
                        option_index
                    ]
                )

                mapped_count += 1

        except Exception as e:

            print(
                f"Failed mapping "
                f"Q{qno}: {e}"
            )

    print(
        f"Answers mapped: "
        f"{mapped_count}"
    )

    return questions


def main():

    print("\n======================")

    print(
        "BATCH PDF EXTRACTION"
    )

    print("======================")

    pdf_paths = get_pdf_paths()

    print(
        f"\nPDFs found: "
        f"{len(pdf_paths)}"
    )

    all_questions = []

    successful_pdfs = 0

    failed_pdfs = 0

    for pdf_path in pdf_paths:

        try:

            questions = process_pdf(
                pdf_path
            )

            all_questions.extend(
                questions
            )

            successful_pdfs += 1

        except Exception as e:

            failed_pdfs += 1

            print(
                f"\nFAILED: "
                f"{pdf_path.name}"
            )

            print(
                f"Reason: {e}\n"
            )

    print(
        "\n======================"
    )

    print(
        "BATCH SUMMARY"
    )

    print("======================")

    print(
        f"Successful PDFs: "
        f"{successful_pdfs}"
    )

    print(
        f"Failed PDFs: "
        f"{failed_pdfs}"
    )

    print(
        f"Total Questions: "
        f"{len(all_questions)}"
    )

    # STEP 4
    # WRITE MASTER EXCEL

    output_path = (
        Path("data/extracted")
        / "extracted_questions.xlsx"
    )

    print(
        "\n[4] Writing master Excel..."
    )

    writer = ExcelWriter()

    writer.write(
        questions=all_questions,
        output_path=str(
            output_path
        ),
    )

    print(
        "\n======================"
    )

    print(
        "Extraction complete"
    )

    print(
        f"Output: {output_path}"
    )

    print(
        "======================\n"
    )


if __name__ == "__main__":
    main()