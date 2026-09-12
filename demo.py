"""Small CLI demo — prints a table of pattern/string pairs and whether this
from-scratch engine matches them (double-checked against `re` alongside it)."""

import re

from regex_engine import fullmatch

DEMO_CASES = [
    ("ab*c", "ac"),
    ("ab*c", "abbbbc"),
    ("ab*c", "adc"),
    ("colou?r", "colour"),
    ("cat|dog", "bird"),
    ("(ab)+", "ababab"),
    ("a(b|c)*d", "abccbd"),
    (r"a\.b", "a.b"),
    ("((a|b)c)+", "acbcac"),
    ("(a?)*b", "aaab"),
]

if __name__ == "__main__":
    print(f"{'pattern':<14}{'string':<12}{'ours':<8}{'re':<8}")
    print("-" * 42)
    for pattern, text in DEMO_CASES:
        ours = fullmatch(pattern, text)
        reference = re.fullmatch(pattern, text) is not None
        flag = "OK" if ours == reference else "MISMATCH"
        print(f"{pattern:<14}{text:<12}{str(ours):<8}{str(reference):<8}{flag}")
