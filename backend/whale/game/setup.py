"""Round setup: seed -> hidden state, final value, and private clues (PRD §7.2)."""

from __future__ import annotations

import random
import secrets
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from .dealing import Clue, answer_questions, choose_balanced, choose_one_card_each
from .posterior import Belief, HasLikelihood, StateSpace, belief, state_space
from .recipes import Recipe


class Dealing(StrEnum):
    ONE_CARD_EACH = "one_card_each"  # prototype, PRD §42
    BALANCED = "balanced"  # Insider mode, PRD §7.5


def new_seed() -> int:
    """Cryptographically random round seed. Never leaves the server before the reveal."""
    return secrets.randbits(64)


@dataclass(frozen=True, slots=True)
class RoundSetup:
    recipe: Recipe
    seed: int
    state: tuple[int, ...]
    final_value: int
    clues: dict[str, Clue]

    @property
    def space(self) -> StateSpace:
        return state_space(self.recipe)

    def player_belief(self, player: str, public: Iterable[HasLikelihood] = ()) -> Belief:
        """E[V | public info + this player's clue], with spread and distribution."""
        return belief(self.space, (self.clues[player].answer, *public))

    def public_belief(self, public: Iterable[HasLikelihood] = ()) -> Belief:
        return belief(self.space, public)


def setup_round(
    recipe: Recipe,
    players: Sequence[str],
    seed: int,
    dealing: Dealing = Dealing.ONE_CARD_EACH,
) -> RoundSetup:
    # Separate streams, so choosing questions consumes no randomness that the
    # hidden state depends on and vice versa. Same seed -> same round.
    root = random.Random(seed)
    question_rng, state_rng, answer_rng, flavor_rng = (random.Random(root.getrandbits(64)) for _ in range(4))

    if dealing is Dealing.ONE_CARD_EACH:
        questions = choose_one_card_each(recipe, players, question_rng)
    else:
        questions = choose_balanced(recipe, players, question_rng)

    state = recipe.sample_state(state_rng)
    clues = answer_questions(state_space(recipe), questions, state, answer_rng, flavor_rng)
    return RoundSetup(recipe=recipe, seed=seed, state=state, final_value=recipe.value(state), clues=clues)
