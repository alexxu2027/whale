"""Choosing and answering clue questions (PRD §7.3, §7.5).

Choosing questions never sees the hidden state; that is what keeps every
fair value exact (see ``questions.py``). The functions are split so this is
structural: ``choose_*`` functions take no state argument at all.
"""

from __future__ import annotations

import functools
import itertools
import random
from collections.abc import Sequence
from dataclasses import dataclass

from .flavor import flavor_text
from .posterior import StateSpace, state_space, strength
from .questions import (
    Answer,
    CompareQ,
    ExactQ,
    Question,
    RangeQ,
    RumorQ,
    SignQ,
    SumRangeQ,
    TotalQ,
)
from .recipes import Recipe


@dataclass(frozen=True, slots=True)
class Clue:
    answer: Answer
    flavor: str  # in-world line, e.g. "The royal collector is not interested."
    precise: str  # exact statement, e.g. "Demand is negative"
    strength: float  # ex-ante, PRD §7.4


@dataclass(frozen=True, slots=True)
class RatedQuestion:
    question: Question
    strength: float


@functools.cache
def question_catalog(recipe: Recipe) -> tuple[RatedQuestion, ...]:
    """Every question the dealer may ask for this recipe, with its strength."""
    space = state_space(recipe)
    k = len(recipe.components)
    qs: list[Question] = []
    for i in range(k):
        qs.append(ExactQ(i))
        qs.append(SignQ(i))
        for width in (3, 4, 5):
            qs.extend(RangeQ(i, width, offset) for offset in range(width))
    # Comparisons have ~0 strength on their own (by symmetry they don't move
    # E[V]); they're kept for combination with other clues and future modes.
    for i, j in itertools.permutations(range(k), 2):
        qs.append(CompareQ(i, j))
    for i, j in itertools.combinations(range(k), 2):
        for width in (5, 7):
            qs.extend(SumRangeQ(i, j, width, offset) for offset in range(width))
    lo, hi = recipe.min_value, recipe.max_value
    thresholds = range(lo + (hi - lo) // 4, hi - (hi - lo) // 4 + 1)
    qs.extend(TotalQ(t) for t in thresholds)
    for p in (70, 80):
        qs.extend(RumorQ(SignQ(i), p) for i in range(k))
        qs.extend(RumorQ(TotalQ(t), p) for t in thresholds)
    return tuple(RatedQuestion(q, strength(space, q)) for q in qs)


def choose_one_card_each(recipe: Recipe, players: Sequence[str], rng: random.Random) -> dict[str, Question]:
    """Prototype dealing (PRD §42): each player sees one starting driver exactly.

    Starting drivers are shuffled and handed out in order, so with as many
    players as starting drivers everyone sees a different one. Drivers kept
    for runners (PRD §7.7) are never dealt at the start.
    """
    order = list(recipe.starting_drivers)
    rng.shuffle(order)
    return {p: ExactQ(order[n % len(order)]) for n, p in enumerate(players)}


def choose_balanced(
    recipe: Recipe,
    players: Sequence[str],
    rng: random.Random,
    strength_range: tuple[float, float] = (0.15, 0.40),
) -> dict[str, Question]:
    """Insider-mode dealing: every clue's strength is within ``strength_range``.

    Prefers questions about components nobody else has been asked about, so
    the table's pooled information tends to cover the whole value.
    """
    lo, hi = strength_range
    eligible = [rq.question for rq in question_catalog(recipe) if lo <= rq.strength <= hi]
    if not eligible:
        raise ValueError(f"no questions with strength in {strength_range}")
    used: set[int] = set()
    chosen: dict[str, Question] = {}
    for p in players:
        fresh = [q for q in eligible if q.components and not (q.components & used)]
        q = rng.choice(fresh or eligible)
        chosen[p] = q
        used |= q.components
    return chosen


def answer_questions(
    space: StateSpace,
    questions: dict[str, Question],
    state: tuple[int, ...],
    answer_rng: random.Random,
    flavor_rng: random.Random,
) -> dict[str, Clue]:
    s = space.index_of(state)
    clues: dict[str, Clue] = {}
    for player, q in questions.items():
        answer = q.answer(space, s, answer_rng)
        clues[player] = Clue(
            answer=answer,
            flavor=flavor_text(space, answer, flavor_rng),
            precise=answer.text(space.recipe),
            strength=strength(space, q),
        )
    return clues
