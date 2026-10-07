"""Tests for dealing clues and setting up rounds (PRD §7.2, §7.5, §42)."""

from __future__ import annotations

import random

import pytest

from whale.game.dealing import choose_balanced, choose_one_card_each
from whale.game.questions import ExactQ
from whale.game.recipes import FOUR_CARDS
from whale.game.setup import Dealing, setup_round

PLAYERS = ["alex", "sam", "maya", "jordan"]


def test_one_card_each_gives_distinct_components() -> None:
    for seed in range(50):
        qs = choose_one_card_each(FOUR_CARDS, PLAYERS, random.Random(seed))
        assert all(isinstance(q, ExactQ) for q in qs.values())
        assert sorted(q.i for q in qs.values()) == [0, 1, 2, 3]


def test_balanced_dealing_respects_strength_and_spreads_components() -> None:
    for seed in range(50):
        r = setup_round(FOUR_CARDS, PLAYERS, seed, Dealing.BALANCED)
        for clue in r.clues.values():
            assert 0.15 <= clue.strength <= 0.40
        comps = [c.answer.question.components for c in r.clues.values()]
        for a, b in zip(comps, comps[1:]):
            assert not (a & b)


def test_balanced_dealing_varies() -> None:
    kinds = {
        type(q).__name__
        for seed in range(200)
        for q in choose_balanced(FOUR_CARDS, PLAYERS, random.Random(seed)).values()
    }
    assert len(kinds) >= 2


def test_setup_is_deterministic_per_seed() -> None:
    a = setup_round(FOUR_CARDS, PLAYERS, 12345)
    b = setup_round(FOUR_CARDS, PLAYERS, 12345)
    assert a == b


@pytest.mark.parametrize("seed", range(20))
def test_prototype_round_clues_and_beliefs(seed: int) -> None:
    r = setup_round(FOUR_CARDS, PLAYERS, seed)
    assert r.final_value == FOUR_CARDS.value(r.state)
    for player, clue in r.clues.items():
        q = clue.answer.question
        assert isinstance(q, ExactQ)
        seen = r.state[q.i]
        name = FOUR_CARDS.components[q.i].name
        assert clue.precise.startswith(f"{name} = ")
        assert clue.flavor
        b = r.player_belief(player)
        assert b.mean == pytest.approx(100 + seen)
        assert b.min <= r.final_value <= b.max  # the truth is always possible
    # Pooling all four exact cards pins the value down completely.
    pooled = r.public_belief([c.answer for c in r.clues.values()])
    assert pooled.mean == pytest.approx(r.final_value)
    assert pooled.sd == pytest.approx(0, abs=1e-6)
