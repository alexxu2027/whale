"""Tests for the information model: recipes, questions, posteriors (PRD §7)."""

from __future__ import annotations

import itertools
import math
import random

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from whale.game.dealing import question_catalog
from whale.game.posterior import belief, state_space, strength
from whale.game.questions import Answer, ExactQ, PartitionQuestion, RumorQ, SignQ, TotalQ
from whale.game.recipes import FOUR_CARDS

from .statements import parse

RECIPE = FOUR_CARDS
SPACE = state_space(RECIPE)
CATALOG = [rq.question for rq in question_catalog(RECIPE)]
ALL_STATES = list(itertools.product(*(c.values for c in RECIPE.components)))


def all_answers() -> list[Answer]:
    return [Answer(q, a) for q in CATALOG for a in range(SPACE.likelihoods(q).shape[0])]


ANSWERS = all_answers()


# -- recipe and prior ---------------------------------------------------------------


def test_four_cards_prior() -> None:
    prior = SPACE.prior_belief
    assert (RECIPE.min_value, RECIPE.max_value) == (80, 120)
    assert SPACE.size == 11**4
    assert prior.mean == pytest.approx(100)
    assert prior.sd == pytest.approx(math.sqrt(40))  # 4 components, each Var = 10
    assert sum(p for _, p in prior.distribution) == pytest.approx(1)


def test_sample_state_in_range() -> None:
    rng = random.Random(0)
    for _ in range(200):
        s = RECIPE.sample_state(rng)
        assert RECIPE.min_value <= RECIPE.value(s) <= RECIPE.max_value


# -- questions ----------------------------------------------------------------------


@pytest.mark.parametrize("q", CATALOG, ids=repr)
def test_likelihood_columns_sum_to_one(q) -> None:
    L = SPACE.likelihoods(q)
    np.testing.assert_allclose(L.sum(axis=0), 1.0)
    assert (L >= 0).all()
    assert (L.sum(axis=1) > 0).all(), "every answer must be possible"


def test_every_answer_text_parses_and_matches_likelihood() -> None:
    """The precise text players see means exactly what the math assumes."""
    rng = random.Random(1)
    sample = rng.sample(ALL_STATES, 300)
    for ans in ANSWERS:
        lik = parse(RECIPE, ans.text(RECIPE))
        row = ans.likelihood(SPACE)
        for s in sample:
            assert row[SPACE.index_of(s)] == pytest.approx(lik(s)), (ans.text(RECIPE), s)


def test_truthful_answers_are_true() -> None:
    rng = random.Random(2)
    for q in CATALOG:
        if not isinstance(q, PartitionQuestion):
            continue
        for _ in range(20):
            s = rng.choice(ALL_STATES)
            ans = q.answer(SPACE, SPACE.index_of(s), rng)
            assert parse(RECIPE, ans.text(RECIPE))(s) == 1.0


def test_answer_text_examples() -> None:
    assert Answer(ExactQ(2), 9).text(RECIPE) == "Export Demand = +4"
    assert Answer(ExactQ(0), 5).text(RECIPE) == "Weather = 0"
    assert Answer(SignQ(1), 1).text(RECIPE) == "Supply Report is not negative"
    assert Answer(TotalQ(105), 0).text(RECIPE) == "The settlement price is below 105"
    assert Answer(RumorQ(SignQ(2), 70), 0).text(RECIPE) == "Rumor (70% reliable): Export Demand is negative"


# -- posteriors ---------------------------------------------------------------------


def brute_force(texts: list[str]) -> tuple[float, float]:
    """Mean and sd of V by enumerating every state, from clue text alone."""
    liks = [parse(RECIPE, t) for t in texts]
    w_sum = m1 = m2 = 0.0
    for s in ALL_STATES:
        w = 1.0
        for lik in liks:
            w *= lik(s)
        if w:
            v = RECIPE.value(s)
            w_sum += w
            m1 += w * v
            m2 += w * v * v
    mean = m1 / w_sum
    return mean, math.sqrt(max(0.0, m2 / w_sum - mean * mean))


def test_exact_card_posterior() -> None:
    for i, v in itertools.product(range(4), (-5, 0, 4)):
        b = belief(SPACE, [Answer(ExactQ(i), v + 5)])
        assert b.mean == pytest.approx(100 + v)
        assert b.sd == pytest.approx(math.sqrt(30))  # three unseen cards
    pooled = [Answer(ExactQ(i), v + 5) for i, v in enumerate((4, -2, 1, 3))]
    b = belief(SPACE, pooled)
    assert (b.mean, b.sd, b.min, b.max) == (pytest.approx(106), pytest.approx(0), 106, 106)


@settings(max_examples=40, deadline=None)
@given(st.lists(st.sampled_from(ANSWERS), min_size=1, max_size=3))
def test_posterior_matches_brute_force(answers: list[Answer]) -> None:
    texts = [a.text(RECIPE) for a in answers]
    try:
        mean, sd = brute_force(texts)
    except ZeroDivisionError:
        with pytest.raises(ValueError):
            belief(SPACE, answers)
        return
    b = belief(SPACE, answers)
    assert b.mean == pytest.approx(mean, abs=1e-9)
    assert b.sd == pytest.approx(sd, abs=1e-9)


def test_strength_matches_definition() -> None:
    """strength = 1 - E[Var(V | answer)] / Var(V), computed the slow way."""
    rng = random.Random(3)
    prior_var = SPACE.prior_belief.sd**2
    for q in rng.sample(CATALOG, 25) + [ExactQ(0)]:
        L = SPACE.likelihoods(q)
        expected_var = 0.0
        for a in range(L.shape[0]):
            p_a = float(L[a] @ SPACE.prior)
            expected_var += p_a * belief(SPACE, [Answer(q, a)]).sd ** 2
        assert strength(SPACE, q) == pytest.approx(1 - expected_var / prior_var, abs=1e-9)
    assert strength(SPACE, ExactQ(0)) == pytest.approx(0.25)


@pytest.mark.parametrize("q", [RumorQ(SignQ(2), 70), RumorQ(TotalQ(104), 80), SignQ(0)], ids=repr)
def test_answer_generation_is_calibrated(q) -> None:
    """Monte Carlo: among rounds that produced an answer, the average final
    value matches that answer's posterior mean. This checks that answers are
    generated by exactly the process the posterior assumes."""
    rng = random.Random(4)
    by_answer: dict[int, list[int]] = {}
    for _ in range(20_000):
        s = RECIPE.sample_state(rng)
        a = q.answer(SPACE, SPACE.index_of(s), rng)
        by_answer.setdefault(a.index, []).append(RECIPE.value(s))
    for a, values in by_answer.items():
        b = belief(SPACE, [Answer(q, a)])
        se = b.sd / math.sqrt(len(values))
        assert abs(sum(values) / len(values) - b.mean) < 4 * se
