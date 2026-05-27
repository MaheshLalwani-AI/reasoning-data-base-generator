from pathlib import Path

from dotenv import load_dotenv

from extraction.answer_detector import (
    AnswerDetector,
)

from extraction.excel_writer import (
    ExcelWriter,
)

from extraction.extractor import (
    PDFExtractor,
)

from extraction.parsers.metadata_parser import (
    QuestionParser as MetadataParser,
)

from extraction.parsers.plain_mcq_parser import (
    QuestionParser as UniversalParser,
)


def get_pdf_paths() -> list[Path]:

    pdf_folder = Path(
        "data/pdfs"
    )

    pdf_files = sorted(
        pdf_folder.glob("*.pdf")
    )

    if not pdf_files:

        raise FileNotFoundError(
            "No PDFs found in data/pdfs"
        )

    return pdf_files


def choose_parser(
    pages,
):

    sample_text = ""

    for page in pages[:3]:

        blocks = page.get(
            "blocks",
            [],
        )

        for block in blocks:

            sample_text += (
                block.get(
                    "text",
                    "",
                )
                + "\n"
            )

    if (
        "Question Number"
        in sample_text
        and
        "Question Id"
        in sample_text
    ):

        print(
            "Using metadata parser"
        )

        return MetadataParser()

    print(
        "Using universal parser"
    )

    return UniversalParser()


def process_pdf(
    pdf_path: Path,
):

    print(
        "\n======================="
    )

    print(
        f"PROCESSING: "
        f"{pdf_path.name}"
    )

    print(
        "=======================\n"
    )

    # STEP 1

    print(
        "[1] Extracting PDF..."
    )

    extractor = PDFExtractor(
        pdf_path=str(
            pdf_path
        )
    )

    pages = (
        extractor.extract_pages()
    )

    print(
        f"Pages extracted: "
        f"{len(pages)}\n"
    )

    # STEP 2

    print(
        "[2] Parsing questions..."
    )

    parser = choose_parser(
        pages
    )

    questions = (
        parser.parse_pages(
            pages
        )
    )

    print(
        f"Questions parsed: "
        f"{len(questions)}\n"
    )

    exam_name = pdf_path.stem

    for question in questions:

        question.exam_name = (
            exam_name
        )

    # STEP 3

    print(
        "[3] Detecting answers..."
    )

    detector = AnswerDetector(
        pdf_path=str(
            pdf_path
        )
    )

    answers = (
        detector.detect_answers()
    )

    print(
        f"Answers detected: "
        f"{len(answers)}\n"
    )

    for question in questions:

        qno = (
            question.question_number
        )

        if qno not in answers:
            continue

        try:

            option_number = int(
                answers[qno]
            )

            option_index = (
                option_number - 1
            )

            if (
                0
                <= option_index
                < len(
                    question.options
                )
            ):

                question.correct_answer = (
                    question.options[
                        option_index
                    ]
                )

        except Exception:
            pass

    return questions


def main():

    load_dotenv()

    pdf_paths = get_pdf_paths()

    print(
        f"\nPDFs found: "
        f"{len(pdf_paths)}\n"
    )

    all_questions = []

    for pdf_path in pdf_paths:

        try:

            questions = process_pdf(
                pdf_path
            )

            all_questions.extend(
                questions
            )

        except Exception as e:

            print(
                f"\nFAILED: "
                f"{pdf_path.name}"
            )

            print(e)

    output_path = Path(
        "data/extracted/extracted_questions.xlsx"
    )

    print(
        "\n[4] Writing Excel..."
    )

    writer = ExcelWriter()

    writer.write(
        questions=all_questions,
        output_path=str(
            output_path
        ),
    )

    print(
        "\n======================="
    )

    print(
        "EXCEL GENERATED"
    )

    print(
        f"Output: "
        f"{output_path}"
    )

    print(
        "=======================\n"
    )


if __name__ == "__main__":
    main()