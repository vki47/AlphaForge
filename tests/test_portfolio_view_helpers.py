import pandas as pd

from alphaforge.services.view_helpers import correlation_summary, parse_allocations


def test_parse_allocations_normalizes_symbols_and_filters_spaces():
    parsed = parse_allocations(" aapl:0.6 , msft:0.4 ")

    assert parsed == {"AAPL": 0.6, "MSFT": 0.4}


def test_parse_allocations_rejects_invalid_inputs():
    assert parse_allocations("AAPL") == {}
    assert parse_allocations("AAPL:not-a-number") == {}
    assert parse_allocations("AAPL:-1") == {}
    assert parse_allocations(" :0.5") == {}


def test_correlation_summary_handles_short_or_empty_matrix():
    empty = pd.DataFrame()
    one_col = pd.DataFrame({"AAPL": [1.0]})

    assert correlation_summary(empty) == {
        "average_pairwise_corr": 0.0,
        "top_pair": "N/A",
        "top_pair_corr": 0.0,
    }
    assert correlation_summary(one_col) == {
        "average_pairwise_corr": 0.0,
        "top_pair": "N/A",
        "top_pair_corr": 0.0,
    }


def test_correlation_summary_reports_average_and_top_pair():
    corr = pd.DataFrame(
        [
            [1.0, 0.2, 0.8],
            [0.2, 1.0, 0.1],
            [0.8, 0.1, 1.0],
        ],
        columns=["AAPL", "MSFT", "NVDA"],
        index=["AAPL", "MSFT", "NVDA"],
    )

    summary = correlation_summary(corr)

    assert summary["top_pair"] == "AAPL-NVDA"
    assert summary["top_pair_corr"] == 0.8
    assert summary["average_pairwise_corr"] == (0.2 + 0.8 + 0.1) / 3
