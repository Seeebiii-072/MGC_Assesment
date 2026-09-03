"""
test_questions.py
------------------
Runs the 5 assessment questions through the assistant and prints the
result for each, so correctness can be checked and demoed quickly.

Run with:
    python test_questions.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assistant import answer_question

TEST_CASES = [
    {
        "question": "What is the base price of a 2-bed in Block B?",
        "expected_behaviour": "Direct lookup: PKR 22,425,000, sourced to the Price List.",
    },
    {
        "question": "What is the total price for a Margalla-facing corner unit, floor 15, 2-bed Block B?",
        "expected_behaviour": "Calculation: base price + 6% Margalla + 3% corner + 4% floor-band premium.",
    },
    {
        "question": "What's the transfer fee?",
        "expected_behaviour": "Conflict: Price List says 2%, Booking FAQ says 2.5% - both must be shown.",
    },
    {
        "question": "What is the rental yield on a 1-bed?",
        "expected_behaviour": "Not found: documents explicitly say yield is not published.",
    },
    {
        "question": "Who is the anchor tenant?",
        "expected_behaviour": "Explicitly unconfirmed per the brochure - must not be invented.",
    },
]


def main():
    for i, case in enumerate(TEST_CASES, start=1):
        print("=" * 70)
        print(f"Test {i}")
        print(f"Question: {case['question']}")
        print(f"Expected behaviour: {case['expected_behaviour']}")
        print("-" * 70)

        result = answer_question(case["question"])

        print(f"Answer:\n{result['answer']}\n")
        print(f"Status: {result['status']}")
        if result.get("calculation"):
            print(f"Calculation:\n{result['calculation']}")
        print("Sources:")
        if result["sources"]:
            for s in result["sources"]:
                print(f"  - {s}")
        else:
            print("  - None")
        print()


if __name__ == "__main__":
    main()
