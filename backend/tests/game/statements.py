"""An independent interpreter for clue text, used to brute-force posteriors.

It reads the *precise statement players see* and evaluates it on a state,
without using any of the question classes. If the text ever disagreed with
the math, posteriors computed from text would disagree with the engine's.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from whale.game.recipes import Recipe

State = tuple[int, ...]
Likelihood = Callable[[State], float]

_NUM = r"([+-]?\d+)"


def _term(recipe: Recipe, expr: str) -> Callable[[State], int]:
    names = [n.strip() for n in expr.split("+")]
    idx = [next(i for i, c in enumerate(recipe.components) if c.name == n) for n in names]
    return lambda s: sum(s[i] for i in idx)


def parse(recipe: Recipe, text: str) -> Likelihood:
    if m := re.fullmatch(r"Rumor \((\d+)% reliable\): (.*)", text):
        p = int(m.group(1)) / 100
        inner = parse(recipe, m.group(2))
        return lambda s: p if inner(s) else 1 - p

    total = f"The {recipe.value_name}"
    if m := re.fullmatch(rf"{total} is at least {_NUM}", text):
        t = int(m.group(1))
        return lambda s: float(recipe.value(s) >= t)
    if m := re.fullmatch(rf"{total} is below {_NUM}", text):
        t = int(m.group(1))
        return lambda s: float(recipe.value(s) < t)

    if m := re.fullmatch(r"(.+) is between ([+-]?\d+|0) and ([+-]?\d+|0)", text):
        f, lo, hi = _term(recipe, m.group(1)), int(m.group(2)), int(m.group(3))
        assert lo < hi, text
        return lambda s: float(lo <= f(s) <= hi)
    if m := re.fullmatch(r"(.+) = ([+-]?\d+|0)", text):
        f, v = _term(recipe, m.group(1)), int(m.group(2))
        return lambda s: float(f(s) == v)
    if m := re.fullmatch(r"(.+) is not negative", text):
        f = _term(recipe, m.group(1))
        return lambda s: float(f(s) >= 0)
    if m := re.fullmatch(r"(.+) is negative", text):
        f = _term(recipe, m.group(1))
        return lambda s: float(f(s) < 0)
    if m := re.fullmatch(r"(.+) is at least as high as (.+)", text):
        a, b = _term(recipe, m.group(1)), _term(recipe, m.group(2))
        return lambda s: float(a(s) >= b(s))
    if m := re.fullmatch(r"(.+) is lower than (.+)", text):
        a, b = _term(recipe, m.group(1)), _term(recipe, m.group(2))
        return lambda s: float(a(s) < b(s))
    raise ValueError(f"unparseable clue text: {text!r}")
