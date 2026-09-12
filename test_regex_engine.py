"""
Tests for regex_engine.py.

The strongest check here isn't hand-picked expected values — it's
cross-validation against Python's own `re` module. Every pattern this engine
supports (`. * + ? | ()` plus backslash-escapes) is valid syntax in `re` too,
so for each (pattern, string) pair we can assert our engine agrees with
`re.fullmatch`. `re` is only imported in this test file — never in
regex_engine.py itself, which is written entirely from scratch.
"""

import re
import unittest

from regex_engine import RegexSyntaxError, compile as regex_compile, fullmatch


# (pattern, text) pairs — a mix of expected-match and expected-reject cases,
# covering literals, '.', '*', '+', '?', '|', groups, escapes, and nesting.
CROSS_CHECK_CASES = [
    ("abc", "abc"),
    ("abc", "abd"),
    ("a.c", "abc"),
    ("a.c", "ac"),
    ("ab*c", "ac"),
    ("ab*c", "abc"),
    ("ab*c", "abbbbc"),
    ("ab*c", "adc"),
    ("ab+c", "ac"),
    ("ab+c", "abc"),
    ("ab+c", "abbc"),
    ("colou?r", "color"),
    ("colou?r", "colour"),
    ("colou?r", "colouur"),
    ("cat|dog", "cat"),
    ("cat|dog", "dog"),
    ("cat|dog", "bird"),
    ("(ab)+", "ababab"),
    ("(ab)+", "aba"),
    ("(ab)+", ""),
    ("a(b|c)*d", "ad"),
    ("a(b|c)*d", "abccbd"),
    ("a(b|c)*d", "abx"),
    (r"a\.b", "a.b"),
    (r"a\.b", "aXb"),
    ("((a|b)c)+", "acbc"),
    ("((a|b)c)+", "acx"),
    ("a*", ""),
    ("a*", "aaaa"),
    ("", ""),
    ("", "x"),
    ("(a?)*b", "aaab"),  # inner group can match empty — exercises the zero-width guard
    ("(a?)*b", "b"),
    ("x+y*z?", "xz"),
    ("x+y*z?", "xxxyyyz"),
    ("x+y*z?", "yz"),
    ("go(pher)?", "go"),
    ("go(pher)?", "gopher"),
    ("go(pher)?", "goph"),
]


class TestCrossCheckAgainstReModule(unittest.TestCase):
    """The actual DoD check: 15+ pattern/string pairs, correctly
    matched/rejected — verified objectively against `re.fullmatch`
    rather than hand-computed expectations."""

    def test_agrees_with_re_fullmatch_on_every_case(self):
        self.assertGreaterEqual(len(CROSS_CHECK_CASES), 15)
        mismatches = []
        for pattern, text in CROSS_CHECK_CASES:
            ours = fullmatch(pattern, text)
            reference = re.fullmatch(pattern, text) is not None
            if ours != reference:
                mismatches.append((pattern, text, ours, reference))
        self.assertEqual(
            mismatches, [], f"Disagreed with re.fullmatch on: {mismatches}"
        )


class TestIndividualFeatures(unittest.TestCase):
    """Same cases, split out so a failure names the exact feature broken."""

    def test_literal_concatenation(self):
        self.assertTrue(fullmatch("abc", "abc"))
        self.assertFalse(fullmatch("abc", "abd"))

    def test_dot_matches_exactly_one_char(self):
        self.assertTrue(fullmatch("a.c", "abc"))
        self.assertFalse(fullmatch("a.c", "ac"))
        self.assertFalse(fullmatch("a.c", "abbc"))

    def test_star_zero_or_more(self):
        self.assertTrue(fullmatch("ab*c", "ac"))
        self.assertTrue(fullmatch("ab*c", "abbbbbc"))
        self.assertFalse(fullmatch("ab*c", "adc"))

    def test_plus_one_or_more(self):
        self.assertFalse(fullmatch("ab+c", "ac"))
        self.assertTrue(fullmatch("ab+c", "abc"))
        self.assertTrue(fullmatch("ab+c", "abbbc"))

    def test_question_zero_or_one(self):
        self.assertTrue(fullmatch("colou?r", "color"))
        self.assertTrue(fullmatch("colou?r", "colour"))
        self.assertFalse(fullmatch("colou?r", "colouur"))

    def test_alternation(self):
        self.assertTrue(fullmatch("cat|dog", "cat"))
        self.assertTrue(fullmatch("cat|dog", "dog"))
        self.assertFalse(fullmatch("cat|dog", "catdog"))

    def test_grouping_with_quantifier(self):
        self.assertTrue(fullmatch("(ab)+", "ababab"))
        self.assertFalse(fullmatch("(ab)+", "abab a"))

    def test_nested_groups_and_alternation(self):
        self.assertTrue(fullmatch("((a|b)c)+", "acbcac"))
        self.assertFalse(fullmatch("((a|b)c)+", "acd"))

    def test_escaped_special_char_is_literal(self):
        self.assertTrue(fullmatch(r"a\.b", "a.b"))
        self.assertFalse(fullmatch(r"a\.b", "aXb"))

    def test_star_of_group_that_can_match_empty_does_not_hang(self):
        # (a?)* — the inner group can match "" every time; a naive
        # implementation loops forever here.
        self.assertTrue(fullmatch("(a?)*b", "aaab"))
        self.assertTrue(fullmatch("(a?)*b", "b"))


class TestMatchAndSearch(unittest.TestCase):
    def test_match_is_prefix_anchored_only(self):
        pattern = regex_compile("ab")
        self.assertTrue(pattern.match("abcdef"))
        self.assertFalse(pattern.fullmatch("abcdef"))

    def test_search_finds_pattern_anywhere(self):
        pattern = regex_compile("cd")
        self.assertTrue(pattern.search("abcdef"))
        self.assertFalse(pattern.search("abxyef"))


class TestSyntaxErrors(unittest.TestCase):
    def test_unbalanced_open_paren_raises(self):
        with self.assertRaises(RegexSyntaxError):
            regex_compile("(ab")

    def test_unbalanced_close_paren_raises(self):
        with self.assertRaises(RegexSyntaxError):
            regex_compile("ab)")

    def test_dangling_quantifier_raises(self):
        with self.assertRaises(RegexSyntaxError):
            regex_compile("*abc")

    def test_dangling_escape_raises(self):
        with self.assertRaises(RegexSyntaxError):
            regex_compile("ab\\")


if __name__ == "__main__":
    unittest.main()
