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

from extraction.image_extractor import (
    PageImageExtractor,
)

from extraction.parsers.metadata_parser import (
    QuestionParser as MetadataParser,
)

from extraction.parsers.plain_mcq_parser import (
    QuestionParser as UniversalParser,
)

from classification import (
    RegexClassifier,
    LLMClassifier,
)


IMAGE_BASED_TOPICS = {
    "Mirror Image",
    "Water Image",
    "Paper Folding",
    "Paper Cutting",
    "Embedded Figures",
    "Hidden Figures",
    "Counting Figures",
    "Figure Series",
    "Figure Analogy (Non-Verbal)",
    "Figure Classification (Non-Verbal)",
    "Figure Matrix",
    "Pattern Completion",
    "Image Formation",
    "Image Analysis",
    "Dot Situation",
    "Rule Detection",
    "Cube and Dice (Standard)",
    "Cube and Dice (Open / Net)",
    "Cube Construction (Painted Cube)",
    "Cube Construction (Cut Cube)",
    "Venn Diagram (Classification)",
    "Venn Diagram (Data Based)",
    "Venn Diagram (Set Theory)",
    "Figure Classification",
}


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


def choose_parser(pages):

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
        "Question Number" in sample_text
        and "Question Id" in sample_text
    ):

        print("Using metadata parser")

        return MetadataParser()

    print("Using universal parser")

    return UniversalParser()


def process_pdf(
    pdf_path: Path,
    regex_clf: RegexClassifier,
    llm_clf: LLMClassifier,
):

    print(
        "\n======================="
    )

    print(
        f"PROCESSING: {pdf_path.name}"
    )

    print(
        "=======================\n"
    )

    # =========================================
    # STEP 1 - extract pages
    # =========================================
    print("[1] Extracting PDF...")

    extractor = PDFExtractor(
        pdf_path=str(pdf_path)
    )

    pages = extractor.extract_pages()

    print(
        f"Pages extracted: "
        f"{len(pages)}\n"
    )

    # =========================================
    # STEP 1b - extract embedded images
    # =========================================
    print("[1b] Extracting images...")

    image_extractor = PageImageExtractor(
        pdf_path=str(pdf_path),
        exam_name=pdf_path.stem,
    )

    page_images = (
        image_extractor.extract()
    )

    print(
        f"Pages with images: "
        f"{len(page_images)}\n"
    )

    # =========================================
    # STEP 2 - parse questions
    # =========================================
    print("[2] Parsing questions...")

    parser = choose_parser(pages)

    questions = parser.parse_pages(pages)

    print(
        f"Questions parsed: "
        f"{len(questions)}\n"
    )

    exam_name = pdf_path.stem

    for question in questions:
        question.exam_name = exam_name

    # =========================================
    # STEP 3 - detect answers
    # =========================================
    print("[3] Detecting answers...")

    detector = AnswerDetector(
        pdf_path=str(pdf_path)
    )

    answers = detector.detect_answers()

    print(
        f"Answers detected: "
        f"{len(answers)}\n"
    )

    for question in questions:

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

        except Exception:
            pass

    # =========================================
    # STEP 4 - classify (regex hint + LLM)
    # =========================================
    print(
        "[4] Classifying questions..."
    )

    image_cursor: dict[int, int] = {}

    filtered: list = []

    for question in questions:

        text_for_clf = (
            question.question_text
            + "\n"
            + "\n".join(question.options)
        )

        # ----- cheap regex pre-filter -----
        regex_result = regex_clf.classify(
            text_for_clf
        )

        question.regex_topic = (
            regex_result["regex_topic"]
        )

        # Hard drop: clearly non-reasoning
        # (subject keywords present).
        if (
            regex_result["negative_hits"]
            > 0
        ):
            question.is_reasoning = False
            continue

        # ----- LLM confirms + names topic -----
        llm_result = llm_clf.classify(
            text_for_clf
        )

        llm_says = llm_result[
            "is_reasoning"
        ]

        if llm_says is None:
            # LLM unavailable -> trust
            # the regex hint as a soft signal.
            question.is_reasoning = (
                regex_result[
                    "is_reasoning_hint"
                ]
            )
            question.llm_topic = ""
        else:
            question.is_reasoning = (
                llm_says
            )
            question.llm_topic = (
                llm_result["llm_topic"]
            )

        if not question.is_reasoning:
            continue

        # ----- attach image for non-verbal -----
        topic_for_image = (
            question.llm_topic
            or question.regex_topic
        )

        if (
            topic_for_image
            in IMAGE_BASED_TOPICS
        ):

            pool = page_images.get(
                question.page_number,
                [],
            )

            idx = image_cursor.get(
                question.page_number,
                0,
            )

            if idx < len(pool):

                question.question_image = (
                    pool[idx]
                )

                image_cursor[
                    question.page_number
                ] = idx + 1

        filtered.append(question)

    print(
        f"Reasoning questions kept: "
        f"{len(filtered)} / "
        f"{len(questions)}\n"
    )

    return filtered


def main():

    load_dotenv()

    pdf_paths = get_pdf_paths()

    print(
        f"\nPDFs found: "
        f"{len(pdf_paths)}\n"
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

    for pdf_path in pdf_paths:

        try:

            questions = process_pdf(
                pdf_path,
                regex_clf,
                llm_clf,
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
        "data/extracted/"
        "extracted_questions.xlsx"
    )

    print("\n[5] Writing Excel...")

    writer = ExcelWriter()

    writer.write(
        questions=all_questions,
        output_path=str(output_path),
    )

    print(
        "\n======================="
    )

    print("EXCEL GENERATED")

    print(
        f"Output: {output_path}"
    )

    print(
        "=======================\n"
    )


if __name__ == "__main__":
    main()