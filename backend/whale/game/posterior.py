"""Exact posterior beliefs over the hidden value (PRD §7.4).

The recipe's whole state space is enumerated once (Four Cards: 11^4 = 14,641
states). Every piece of information is a likelihood vector over that space,
so a belief is just ``prior * likelihood_1 * likelihood_2 * ...``, normalized.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import numpy as np

from .recipes import Recipe

if TYPE_CHECKING:
    from .questions import Question


class HasLikelihood(Protocol):
    def likelihood(self, space: StateSpace) -> np.ndarray: ...


class StateSpace:
    def __init__(self, recipe: Recipe) -> None:
        self.recipe = recipe
        axes = [np.array(c.values, dtype=np.int64) for c in recipe.components]
        grids = np.meshgrid(*axes, indexing="ij")
        self.states = np.stack([g.ravel() for g in grids], axis=1)  # (N, k)
        self.size = self.states.shape[0]
        self.prior = np.full(self.size, 1.0 / self.size)
        self.values = recipe.base + self.states.sum(axis=1)
        self.prior_belief = belief(self, ())
        self._lookup = {tuple(int(x) for x in row): i for i, row in enumerate(self.states)}
        self._likelihoods: dict[Question, np.ndarray] = {}

    def index_of(self, state: tuple[int, ...]) -> int:
        return self._lookup[state]

    def column(self, i: int) -> np.ndarray:
        return self.states[:, i]

    def likelihoods(self, question: Question) -> np.ndarray:
        """Cached ``(n_answers, N)`` likelihood matrix for a question."""
        L = self._likelihoods.get(question)
        if L is None:
            L = question.likelihoods(self)
            L.setflags(write=False)
            self._likelihoods[question] = L
        return L


@functools.cache
def state_space(recipe: Recipe) -> StateSpace:
    return StateSpace(recipe)


@dataclass(frozen=True, slots=True)
class Belief:
    mean: float
    sd: float
    min: int  # smallest value with nonzero probability
    max: int
    distribution: tuple[tuple[int, float], ...]  # (value, probability), ascending


def belief(space: StateSpace, info: Iterable[HasLikelihood]) -> Belief:
    w = space.prior.copy()
    for item in info:
        w *= item.likelihood(space)
    return _summarize(space, w)


def _summarize(space: StateSpace, w: np.ndarray) -> Belief:
    total = w.sum()
    if total <= 0:
        raise ValueError("information is inconsistent: no state has positive probability")
    w = w / total
    v = space.values
    mean = float(w @ v)
    var = max(0.0, float(w @ (v * v)) - mean * mean)
    lo = space.recipe.min_value
    probs = np.bincount(v - lo, weights=w, minlength=space.recipe.max_value - lo + 1)
    dist = tuple((lo + i, float(p)) for i, p in enumerate(probs) if p > 0)
    return Belief(mean=mean, sd=math.sqrt(var), min=dist[0][0], max=dist[-1][0], distribution=dist)


def strength(space: StateSpace, question: Question) -> float:
    """Ex-ante share of value variance a question's answer is expected to remove.

    ``1 - E[Var(V | answer)] / Var(V)``, averaged over every answer the
    question could produce, weighted by how likely each answer is. It depends
    only on the question, never on the realized hidden state.
    """
    L = space.likelihoods(question)
    v = space.values.astype(float)
    joint = L * space.prior  # (n_answers, N): P(answer, state)
    p_answer = joint.sum(axis=1)
    m1 = joint @ v
    m2 = joint @ (v * v)
    nz = p_answer > 0
    # sum_a P(a) Var(V|a) = sum_a (m2_a - m1_a^2 / P(a))
    expected_var = float((m2[nz] - m1[nz] ** 2 / p_answer[nz]).sum())
    prior_var = space.prior_belief.sd ** 2
    return 1.0 - expected_var / prior_var
