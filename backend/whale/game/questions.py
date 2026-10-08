"""Clue questions and answers (PRD §7.3).

A clue is generated in two steps:

1. A **question** is chosen without looking at the hidden state
   ("What is Export Demand?", "Is the settlement price at least 105?").
2. The question is **answered** from the hidden state. Each question defines a
   likelihood matrix ``L[answer, state] = P(answer | state)`` whose columns
   sum to 1. Truthful questions put probability 1 on the answer containing
   the state; rumors put ``p`` on the true answer and ``1 - p`` on the other.

Because the question choice carries no information and the answer process is
exactly ``L``, the Bayesian update for receiving an answer is exactly
``prior * L[answer]``. No approximation, no leakage from how clues are picked.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .posterior import StateSpace
    from .recipes import Recipe


def signed(v: int) -> str:
    return "0" if v == 0 else f"{v:+d}"


@dataclass(frozen=True, slots=True)
class Answer:
    question: Question
    index: int

    def likelihood(self, space: StateSpace) -> np.ndarray:
        return space.likelihoods(self.question)[self.index]

    def text(self, recipe: Recipe) -> str:
        """The precise statement shown under the flavor text."""
        return self.question.answer_text(recipe, self.index)


class Question(ABC):
    kind: str

    @abstractmethod
    def likelihoods(self, space: StateSpace) -> np.ndarray:
        """``(n_answers, N)`` matrix; each column sums to 1."""

    @abstractmethod
    def answer_text(self, recipe: Recipe, index: int) -> str: ...

    @property
    @abstractmethod
    def components(self) -> frozenset[int]:
        """Indices of the components this question is about."""

    def answer(self, space: StateSpace, state_index: int, rng: random.Random) -> Answer:
        probs = space.likelihoods(self)[:, state_index]
        r = rng.random()
        acc = 0.0
        for i, p in enumerate(probs):
            acc += p
            if r < acc:
                return Answer(self, i)
        return Answer(self, int(np.flatnonzero(probs)[-1]))  # float round-off guard


class PartitionQuestion(Question):
    """A truthful question: the state space is split into cells, and the
    answer is the cell containing the hidden state."""

    @abstractmethod
    def cells(self, space: StateSpace) -> tuple[np.ndarray, int]:
        """Cell index per state, and the number of cells."""

    def likelihoods(self, space: StateSpace) -> np.ndarray:
        cell, n = self.cells(space)
        L = np.zeros((n, space.size))
        L[cell, np.arange(space.size)] = 1.0
        return L


def _windows(x: np.ndarray, lo: int, width: int, offset: int) -> tuple[np.ndarray, int]:
    """Bucket integers >= lo into windows of ``width``, shifted down by ``offset``."""
    cell = (x - lo + offset) // width
    return cell, int(cell.max()) + 1


def _window_bounds(index: int, lo: int, hi: int, width: int, offset: int) -> tuple[int, int]:
    start = lo - offset + index * width
    return max(lo, start), min(hi, start + width - 1)


# -- truthful questions ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExactQ(PartitionQuestion):
    """What is component i?"""

    i: int
    kind = "exact"

    def cells(self, space: StateSpace) -> tuple[np.ndarray, int]:
        c = space.recipe.components[self.i]
        return space.column(self.i) - c.min, c.max - c.min + 1

    def answer_text(self, recipe: Recipe, index: int) -> str:
        c = recipe.components[self.i]
        return f"{c.name} = {signed(c.min + index)}"

    @property
    def components(self) -> frozenset[int]:
        return frozenset((self.i,))


@dataclass(frozen=True, slots=True)
class SignQ(PartitionQuestion):
    """Is component i negative?"""

    i: int
    kind = "sign"

    def cells(self, space: StateSpace) -> tuple[np.ndarray, int]:
        return (space.column(self.i) >= 0).astype(np.int64), 2

    def answer_text(self, recipe: Recipe, index: int) -> str:
        name = recipe.components[self.i].name
        return f"{name} is not negative" if index else f"{name} is negative"

    @property
    def components(self) -> frozenset[int]:
        return frozenset((self.i,))


@dataclass(frozen=True, slots=True)
class RangeQ(PartitionQuestion):
    """Which window of ``width`` values (grid shifted by ``offset``) holds component i?"""

    i: int
    width: int
    offset: int
    kind = "range"

    def cells(self, space: StateSpace) -> tuple[np.ndarray, int]:
        c = space.recipe.components[self.i]
        return _windows(space.column(self.i), c.min, self.width, self.offset)

    def answer_text(self, recipe: Recipe, index: int) -> str:
        c = recipe.components[self.i]
        lo, hi = _window_bounds(index, c.min, c.max, self.width, self.offset)
        if lo == hi:
            return f"{c.name} = {signed(lo)}"
        return f"{c.name} is between {signed(lo)} and {signed(hi)}"

    @property
    def components(self) -> frozenset[int]:
        return frozenset((self.i,))


@dataclass(frozen=True, slots=True)
class CompareQ(PartitionQuestion):
    """Is component i at least as high as component j?"""

    i: int
    j: int
    kind = "compare"

    def cells(self, space: StateSpace) -> tuple[np.ndarray, int]:
        return (space.column(self.i) >= space.column(self.j)).astype(np.int64), 2

    def answer_text(self, recipe: Recipe, index: int) -> str:
        a, b = recipe.components[self.i].name, recipe.components[self.j].name
        return f"{a} is at least as high as {b}" if index else f"{a} is lower than {b}"

    @property
    def components(self) -> frozenset[int]:
        return frozenset((self.i, self.j))


@dataclass(frozen=True, slots=True)
class SumRangeQ(PartitionQuestion):
    """Which window holds component i + component j?"""

    i: int
    j: int
    width: int
    offset: int
    kind = "sum_range"

    def _bounds(self, recipe: Recipe) -> tuple[int, int]:
        ci, cj = recipe.components[self.i], recipe.components[self.j]
        return ci.min + cj.min, ci.max + cj.max

    def cells(self, space: StateSpace) -> tuple[np.ndarray, int]:
        lo, _ = self._bounds(space.recipe)
        return _windows(space.column(self.i) + space.column(self.j), lo, self.width, self.offset)

    def answer_text(self, recipe: Recipe, index: int) -> str:
        a, b = recipe.components[self.i].name, recipe.components[self.j].name
        lo, hi = _window_bounds(index, *self._bounds(recipe), self.width, self.offset)
        if lo == hi:
            return f"{a} + {b} = {signed(lo)}"
        return f"{a} + {b} is between {signed(lo)} and {signed(hi)}"

    @property
    def components(self) -> frozenset[int]:
        return frozenset((self.i, self.j))


@dataclass(frozen=True, slots=True)
class TotalQ(PartitionQuestion):
    """Is the final value at least ``threshold``?"""

    threshold: int
    kind = "total"

    def cells(self, space: StateSpace) -> tuple[np.ndarray, int]:
        return (space.values >= self.threshold).astype(np.int64), 2

    def answer_text(self, recipe: Recipe, index: int) -> str:
        what = f"The {recipe.value_name}"
        return f"{what} is at least {self.threshold}" if index else f"{what} is below {self.threshold}"

    @property
    def components(self) -> frozenset[int]:
        return frozenset()  # about the total, not any one factor


# -- rumors -----------------------------------------------------------------------


BinaryQuestion = SignQ | CompareQ | TotalQ


@dataclass(frozen=True, slots=True)
class RumorQ(Question):
    """A yes/no question answered truthfully with probability ``reliability_pct``%."""

    inner: BinaryQuestion
    reliability_pct: int
    kind = "rumor"

    def likelihoods(self, space: StateSpace) -> np.ndarray:
        p = self.reliability_pct / 100
        truth = space.likelihoods(self.inner)  # one-hot, 2 rows
        return p * truth + (1 - p) * truth[::-1]

    def answer_text(self, recipe: Recipe, index: int) -> str:
        return f"Rumor ({self.reliability_pct}% reliable): {self.inner.answer_text(recipe, index)}"

    @property
    def components(self) -> frozenset[int]:
        return self.inner.components
