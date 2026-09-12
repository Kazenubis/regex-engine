# Regex Engine (subset)

A regex engine built from scratch — no `re` module anywhere in the engine
itself. Supports `.` `*` `+` `?` `|` `()` and backslash-escaping, matched via
a recursive-descent parser feeding a continuation-passing-style backtracking
matcher.

Real output, cross-checked live against Python's own `re` module:

```
pattern       string      ours    re      
------------------------------------------
ab*c          ac          True    True    OK
ab*c          abbbbc      True    True    OK
ab*c          adc         False   False   OK
colou?r       colour      True    True    OK
cat|dog       bird        False   False   OK
(ab)+         ababab      True    True    OK
a(b|c)*d      abccbd      True    True    OK
a\.b          a.b         True    True    OK
((a|b)c)+     acbcac      True    True    OK
(a?)*b        aaab        True    True    OK
```

## Features

- Literal characters, `.` (any char), `*`/`+`/`?` quantifiers, `|`
  alternation, `()` grouping (including nested), and `\` to escape a literal
  special character
- `fullmatch`, `match` (prefix-anchored), and `search` (unanchored) — same
  names as the standard `re` module, for a familiar interface
- Correctly handles the classic trap: `(a?)*` — a group that can match the
  empty string, repeated with `*` — without looping forever, by detecting
  when a repetition made zero progress and stopping there
- Malformed patterns (unbalanced parens, a dangling `\`, a quantifier with
  nothing to quantify) raise a clear `RegexSyntaxError` instead of crashing
  or silently misbehaving

## Tech Stack

Python 3, standard library only (the test suite additionally imports `re`
— but only to cross-check this engine's answers, never to implement it)

## Getting Started

```bash
git clone https://github.com/Kazenubis/regex-engine.git
cd regex-engine
python3 demo.py
```

Run the tests:

```bash
python3 -m unittest test_regex_engine.py -v
```

## What I Learned

The quantifiers are the part that looks trivial and isn't. A backtracking
`*` can't just "consume greedily then move on" — it has to be willing to
give back characters if consuming them dooms the rest of the pattern (e.g.
`a*a` matching `"aaa"`: naive greedy consumption eats all three `a`s, then
has nothing left for the final required `a`, and has to backtrack one step).
Continuation-passing style is what makes that fall out naturally: every node
is handed "what happens next" as a function, and only returns success once
some continuation actually succeeds — so a `Star` node trying "one more
repetition" and failing can fall back to "zero more repetitions" and hand
off to the rest of the pattern instead, purely by returning `False` and
trying the next option.

The other real trap was `(a?)*`: the inner group can match the empty
string, so a naive `*` implementation calls it forever without ever
advancing `pos`. The fix is a progress check — if a repetition consumed zero
characters, stop repeating rather than recursing again — and
`test_star_of_group_that_can_match_empty_does_not_hang` is there specifically
to make sure that guard doesn't regress.

Cross-checking every test case against `re.fullmatch` instead of hand-typing
expected `True`/`False` values turned out to be the better testing strategy
by far — it caught disagreements I wouldn't have thought to test for by
hand, and it means "correct" here is defined objectively, not by whatever I
assumed while writing the matcher.
