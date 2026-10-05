"""Tests for the new-engine budget tracker (ADE-35): turns/cost/time accounting.

Pure arithmetic, no I/O, no network, no real sleeping.
"""

from __future__ import annotations

from src.engine.budget import (
    TOOL_COST_USD,
    Budget,
    BudgetTracker,
    Spend,
    estimate_budget_for_complexity,
)

# --- AC1 ---------------------------------------------------------------------------------------


def test_spend_remaining_and_fraction_used_do_not_mutate():
    budget = Budget(max_turns=10, max_cost_usd=1.0, max_seconds=100.0)
    spend = Spend(turns=5, cost_usd=0.4, seconds=40.0)

    remaining = spend.remaining(budget)
    assert remaining.turns == 5
    assert remaining.cost_usd == 0.6
    assert remaining.seconds == 60.0

    fractions = spend.fraction_used(budget)
    assert fractions == {"turns": 0.5, "cost": 0.4, "time": 0.4}

    # neither input was mutated
    assert spend.turns == 5
    assert budget.max_turns == 10


def test_remaining_never_goes_negative_on_an_already_exhausted_budget():
    budget = Budget(max_turns=5, max_cost_usd=1.0, max_seconds=10.0)
    spend = Spend(turns=9, cost_usd=5.0, seconds=99.0)  # over budget

    remaining = spend.remaining(budget)
    assert remaining.turns == 0
    assert remaining.cost_usd == 0.0
    assert remaining.seconds == 0.0


def test_fraction_used_guards_against_zero_division():
    budget = Budget(max_turns=0, max_cost_usd=0.0, max_seconds=0.0)
    spend = Spend(turns=0, cost_usd=0.0, seconds=0.0)

    fractions = spend.fraction_used(budget)
    assert fractions == {"turns": 0.0, "cost": 0.0, "time": 0.0}


# --- AC2 ---------------------------------------------------------------------------------------


def test_record_tool_accumulates_turns_and_cost_correctly():
    tracker = BudgetTracker()

    tracker.record_tool("crop_and_read_tool")
    tracker.record_tool("crop_and_read_tool")
    tracker.record_tool("crop_and_read_tool")
    tracker.record_tool("validate_extraction")  # free

    assert tracker.spend.turns == 3
    assert tracker.spend.cost_usd == 3 * TOOL_COST_USD["crop_and_read_tool"]
    assert tracker.tool_history == [
        "crop_and_read_tool",
        "crop_and_read_tool",
        "crop_and_read_tool",
        "validate_extraction",
    ]


# --- AC3 ---------------------------------------------------------------------------------------


def test_unlisted_tool_name_defaults_to_one_turn_zero_cost():
    tracker = BudgetTracker()
    tracker.record_tool("some_future_tool_nobody_has_priced_yet")

    assert tracker.spend.turns == 1
    assert tracker.spend.cost_usd == 0.0


# --- AC4 ---------------------------------------------------------------------------------------


def test_status_recommendations_appear_below_threshold():
    tracker = BudgetTracker(budget=Budget(max_turns=10, max_cost_usd=10.0, max_seconds=1000.0))
    for _ in range(8):
        tracker.record_tool("crop_and_read_tool")

    status = tracker.status()
    assert status["remaining_turns"] == 2
    assert any("Only 2 turns left" in r for r in status["recommendations"])


def test_status_has_no_low_turns_recommendation_when_plenty_remain():
    tracker = BudgetTracker(budget=Budget(max_turns=10, max_cost_usd=10.0, max_seconds=1000.0))
    tracker.record_tool("crop_and_read_tool")  # 1 of 10: well above both low-turns thresholds

    status = tracker.status()
    assert status["remaining_turns"] == 9
    assert not any("turns left" in r for r in status["recommendations"])


# --- AC5 ---------------------------------------------------------------------------------------


def test_estimate_budget_for_complexity_scales_with_zones_and_resolution():
    small = estimate_budget_for_complexity(zone_count=2, image_pixels=500_000)
    many_zones = estimate_budget_for_complexity(zone_count=20, image_pixels=500_000)
    high_res = estimate_budget_for_complexity(zone_count=2, image_pixels=10_000_000)

    assert many_zones.max_turns > small.max_turns
    assert high_res.max_turns > small.max_turns


def test_estimate_budget_for_complexity_caps_runaway_zone_counts():
    normal = estimate_budget_for_complexity(zone_count=20, image_pixels=500_000)
    pathological = estimate_budget_for_complexity(zone_count=10_000, image_pixels=500_000)

    # the zone-count contribution is capped, so an absurd input doesn't blow up max_turns
    assert pathological.max_turns < normal.max_turns + 1000
