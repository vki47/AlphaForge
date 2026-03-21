import pandas as pd
import pytest

from alphaforge.services.view_helpers import run_compare_metrics


def test_calculate_metrics_matches_expected_values():
    frame = pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=4, freq="D"),
            "Close": [100.0, 110.0, 121.0, 115.0],
        }
    )

    total_ret, ann_ret, ann_vol = run_compare_metrics(frame)

    expected_returns = pd.Series([0.1, 0.1, -0.049586776859504134])
    assert total_ret == pytest.approx(15.0)
    assert ann_ret == pytest.approx(float(expected_returns.mean() * 252 * 100))
    assert ann_vol == pytest.approx(float(expected_returns.std() * (252**0.5) * 100))


def test_calculate_metrics_zero_vol_when_only_one_return():
    frame = pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=2, freq="D"),
            "Close": [100.0, 105.0],
        }
    )

    total_ret, ann_ret, ann_vol = run_compare_metrics(frame)

    assert total_ret == pytest.approx(5.0)
    assert ann_ret == pytest.approx(0.05 * 252 * 100)
    assert ann_vol == 0.0
