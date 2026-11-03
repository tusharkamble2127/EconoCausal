"""Unit tests for app.pipeline.optimizer (Volume II Chapter 12, Days 16, 17, 20)."""
from app.pipeline.optimizer import allocate


def test_allocate_small_hand_checked_example():
    """Two customers, one clearly more persuadable than the other.
    With a budget for exactly one $10 discount, the optimizer should
    give the discount to the customer with the higher ITE.
    """
    ite_matrix = {
        1: {0.0: 0.0, 10.0: 0.20},  # highly persuadable
        2: {0.0: 0.0, 10.0: 0.01},  # barely persuadable
    }
    results, total_used = allocate(ite_matrix, budget=10.0)

    chosen = {r.customer_id: r.chosen_discount for r in results}
    assert chosen[1] == 10.0
    assert chosen[2] == 0.0
    assert total_used == 10.0


def test_allocate_never_exceeds_budget():
    ite_matrix = {i: {0.0: 0.0, 10.0: 0.1 + i * 0.01, 20.0: 0.15 + i * 0.01} for i in range(20)}
    budget = 55.0
    results, total_used = allocate(ite_matrix, budget=budget)
    assert total_used <= budget
    assert sum(r.budget_used for r in results) == total_used


def test_allocate_zero_budget_gives_everyone_no_discount():
    ite_matrix = {1: {0.0: 0.0, 10.0: 0.5}, 2: {0.0: 0.0, 10.0: 0.9}}
    results, total_used = allocate(ite_matrix, budget=0.0)
    assert total_used == 0.0
    assert all(r.chosen_discount == 0.0 for r in results)


def test_allocate_empty_matrix_returns_empty():
    results, total_used = allocate({}, budget=100.0)
    assert results == []
    assert total_used == 0.0
