"""
A regex engine built from scratch — no `re` module involved anywhere in this
file. Supports the classic core: `.` (any char), `*` `+` `?` (quantifiers),
`|` (alternation), `()` (grouping), and `\\` (escape a literal special char).

Design: a recursive-descent parser turns the pattern into a small AST, then
a continuation-passing-style (CPS) backtracking matcher walks the AST against
the text. CPS is what makes backtracking quantifiers and alternation work
together correctly — each node is handed "what to try next", and if that
fails, the node is free to try a different way of matching itself before
giving up.
"""


class RegexSyntaxError(ValueError):
    """Raised when a pattern is malformed (unbalanced parens, dangling
    escape, a quantifier with nothing to quantify, etc.)."""


# --------------------------------------------------------------------------
# AST nodes. Each node implements match(text, pos, cont):
#   - `cont` is a function: new_pos -> bool ("does the REST of the pattern
#     succeed if we continue matching from new_pos?")
#   - the node tries to consume input starting at `pos`, and for each way it
#     could do so, calls cont(new_pos); if cont returns True, the node
#     returns True immediately (success found). If every way the node could
#     match still leads to cont failing, the node returns False.
# This is what lets a `*` or `|` backtrack: they don't just "match greedily
# and move on" — they only commit to a particular match once the rest of the
# pattern has confirmed it leads to overall success.
# --------------------------------------------------------------------------


class CharNode:
    """Matches exactly one literal character."""

    def __init__(self, ch):
        self.ch = ch

    def match(self, text, pos, cont):
        if pos < len(text) and text[pos] == self.ch:
            return cont(pos + 1)
        return False

    def __repr__(self):
        return f"Char({self.ch!r})"


class DotNode:
    """Matches exactly one character of any kind."""

    def match(self, text, pos, cont):
        if pos < len(text):
            return cont(pos + 1)
        return False

    def __repr__(self):
        return "Dot()"


class EmptyNode:
    """Matches the empty string — consumes nothing. Used to implement `?`
    (as an alternative branch) and an empty group/term like `()`."""

    def match(self, text, pos, cont):
        return cont(pos)

    def __repr__(self):
        return "Empty()"


class ConcatNode:
    """Matches a sequence of parts, one after another."""

    def __init__(self, parts):
        self.parts = parts

    def match(self, text, pos, cont):
        return self._match_from(0, text, pos, cont)

    def _match_from(self, index, text, pos, cont):
        if index == len(self.parts):
            return cont(pos)
        part = self.parts[index]
        return part.match(text, pos, lambda p: self._match_from(index + 1, text, p, cont))

    def __repr__(self):
        return f"Concat({self.parts!r})"


class AltNode:
    """Matches if ANY branch matches (tried in order — first branch that
    leads to overall success wins; this is what gives `|` its backtracking:
    if branch 1 matches locally but dooms the rest of the pattern, branch 2
    still gets a chance)."""

    def __init__(self, branches):
        self.branches = branches

    def match(self, text, pos, cont):
        for branch in self.branches:
            if branch.match(text, pos, cont):
                return True
        return False

    def __repr__(self):
        return f"Alt({self.branches!r})"


class StarNode:
    """Greedy zero-or-more repetition of `node`, with backtracking: tries to
    match as many repetitions as possible first, and only falls back to
    fewer repetitions if that's the only way the rest of the pattern can
    succeed. Guards against infinite recursion when `node` can match the
    empty string (e.g. `(a?)*`)."""

    def __init__(self, node):
        self.node = node

    def match(self, text, pos, cont):
        def try_more(p):
            def after_one_rep(p2):
                if p2 == p:
                    # Zero-width match (e.g. the inner node matched empty) —
                    # repeating it again would loop forever and adds
                    # nothing, so stop extending and hand off to cont.
                    return cont(p2)
                return try_more(p2)

            if self.node.match(text, p, after_one_rep):
                return True
            # No way to extend with one more repetition (or extending
            # doomed the rest of the match) — stop here, zero more reps.
            return cont(p)

        return try_more(pos)

    def __repr__(self):
        return f"Star({self.node!r})"


# --------------------------------------------------------------------------
# Parser: recursive-descent over the grammar
#   expr   := term ('|' term)*
#   term   := factor*
#   factor := atom ('*' | '+' | '?')?
#   atom   := '(' expr ')' | '.' | '\' any | literal-char
# `+` desugars to Concat([atom, Star(atom)]); `?` desugars to
# Alt([atom, Empty()]) — so the matcher only needs to know about Star, not
# every quantifier separately.
# --------------------------------------------------------------------------

_SPECIAL_CHARS = set("().|*+?\\")


class Parser:
    def __init__(self, pattern):
        self.pattern = pattern
        self.pos = 0

    def peek(self):
        return self.pattern[self.pos] if self.pos < len(self.pattern) else None

    def advance(self):
        c = self.pattern[self.pos]
        self.pos += 1
        return c

    def parse(self):
        node = self.parse_expr()
        if self.pos != len(self.pattern):
            raise RegexSyntaxError(
                f"Unexpected {self.peek()!r} at position {self.pos} in {self.pattern!r}"
            )
        return node

    def parse_expr(self):
        branches = [self.parse_term()]
        while self.peek() == "|":
            self.advance()
            branches.append(self.parse_term())
        return branches[0] if len(branches) == 1 else AltNode(branches)

    def parse_term(self):
        factors = []
        while self.peek() is not None and self.peek() not in "|)":
            factors.append(self.parse_factor())
        if not factors:
            return EmptyNode()
        return factors[0] if len(factors) == 1 else ConcatNode(factors)

    def parse_factor(self):
        atom = self.parse_atom()
        quant = self.peek()
        if quant == "*":
            self.advance()
            return StarNode(atom)
        if quant == "+":
            self.advance()
            return ConcatNode([atom, StarNode(atom)])
        if quant == "?":
            self.advance()
            return AltNode([atom, EmptyNode()])
        return atom

    def parse_atom(self):
        c = self.peek()
        if c is None:
            raise RegexSyntaxError(f"Unexpected end of pattern in {self.pattern!r}")
        if c == "(":
            self.advance()
            node = self.parse_expr()
            if self.peek() != ")":
                raise RegexSyntaxError(f"Missing closing ')' in {self.pattern!r}")
            self.advance()
            return node
        if c == ".":
            self.advance()
            return DotNode()
        if c == "\\":
            self.advance()
            escaped = self.peek()
            if escaped is None:
                raise RegexSyntaxError(f"Dangling '\\' at end of pattern {self.pattern!r}")
            self.advance()
            return CharNode(escaped)
        if c in "*+?":
            raise RegexSyntaxError(
                f"Quantifier {c!r} with nothing to quantify at position {self.pos} in {self.pattern!r}"
            )
        if c == ")":
            raise RegexSyntaxError(f"Unmatched ')' at position {self.pos} in {self.pattern!r}")
        self.advance()
        return CharNode(c)


class Pattern:
    """A compiled pattern — parse once, match many times."""

    def __init__(self, pattern):
        self.pattern = pattern
        self.root = Parser(pattern).parse()

    def fullmatch(self, text):
        """True if the ENTIRE text matches the pattern (anchored at both ends —
        this is the primary, best-defined notion of "matches" for this engine)."""
        return self.root.match(text, 0, lambda p: p == len(text))

    def match(self, text):
        """True if the pattern matches a prefix of text (anchored at the start
        only, like re.match)."""
        return self.root.match(text, 0, lambda p: True)

    def search(self, text):
        """True if the pattern matches anywhere in text (unanchored)."""
        for start in range(len(text) + 1):
            if self.root.match(text, start, lambda p: True):
                return True
        return False

    def __repr__(self):
        return f"Pattern({self.pattern!r})"


def compile(pattern):  # noqa: A001 - deliberately mirrors re.compile's name
    return Pattern(pattern)


def fullmatch(pattern, text):
    return Pattern(pattern).fullmatch(text)


def match(pattern, text):
    return Pattern(pattern).match(text)


def search(pattern, text):
    return Pattern(pattern).search(text)
