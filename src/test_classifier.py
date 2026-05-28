from classification import RegexClassifier


SAMPLES = [
    (
        "Eight people sit around a circular "
        "table facing the centre...",
        "Circular Seating Arrangement",
    ),
    (
        "In a certain code language, FRIEND "
        "is written as HUMJTK. What is the "
        "code for CANDLE?",
        "Letter Coding",
    ),
    (
        "Pointing to a photograph, Ravi said, "
        "'She is the daughter of my father's "
        "only son.' How is she related to Ravi?",
        "Blood Relations",
    ),
    (
        "A girl walks 5 km towards north, "
        "then turns right and walks 3 km...",
        "Direction Sense",
    ),
    (
        "Find the mirror image of the given "
        "figure.",
        "Mirror Image",
    ),
    (
        "Find the synonym of the word "
        "'benevolent'.",
        "Uncategorized",
    ),
]


def main():

    clf = RegexClassifier()

    for text, expected in SAMPLES:

        out = clf.classify(text)

        mark = (
            "OK"
            if out["regex_topic"]
            == expected
            else "MISS"
        )

        print(
            f"[{mark}] expected="
            f"{expected!r:40} "
            f"got={out['regex_topic']!r} "
            f"is_reasoning="
            f"{out['is_reasoning']}"
        )


if __name__ == "__main__":
    main()