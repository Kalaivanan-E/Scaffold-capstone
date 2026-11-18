import pytest

from priority_score import calculate_priority_score


@pytest.mark.parametrize(
    ("severity", "expected_score"),
    [
        ("critical", 80),
        ("warning", 50),
        ("info", 30),
    ],
)
def test_calculate_priority_score_above_threshold_returns_int(severity, expected_score):
    score = calculate_priority_score(severity, metric_value=15, threshold=10)

    assert score == expected_score
    assert isinstance(score, int)


# --- Edge cases added manually ---
def test_unknown_severity_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported severity"):
        calculate_priority_score("emergency", 100, 90)


def test_zero_threshold_raises_value_error():
    with pytest.raises(ValueError, match="threshold must not be zero"):
        calculate_priority_score("critical", 50, 0)


def test_metric_below_threshold_gets_no_bonus():
    assert calculate_priority_score("warning", -20, 10) == 30


def test_metric_at_threshold_gets_no_bonus():
    assert calculate_priority_score("warning", 10, 10) == 30


def test_bonus_is_capped_at_40():
    assert calculate_priority_score("critical", 100, 10) == 100