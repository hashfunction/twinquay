# Copyright 2026 Trieflow LLC. GPL-3.0; see LICENSE.
from dataclasses import replace
from core.cleanup_plan import validate_candidate


class CleanupPlanReview:
    """Fast metadata-only preview; full byte reads run in the execution worker."""

    def __init__(self, plan):
        self.plan = plan
        self.eligibility = tuple(validate_candidate(c, compare=False) for c in plan.candidates)

    def selected_plan(self, indices):
        return replace(
            self.plan,
            candidates=tuple(
                candidate
                for index, candidate in enumerate(self.plan.candidates)
                if index in indices and self.eligibility[index].eligible
            ),
        )
