from alphaforge.services.view_helpers import build_research_report_markdown


def test_build_research_report_markdown_includes_optional_compare_section():
    text = build_research_report_markdown(
        symbol="AAPL",
        start_date="2024-01-01",
        end_date="2024-12-31",
        rows_analyzed=100,
        latest_close=123.45,
        latest_rsi=55.1,
        latest_regime="bull",
        commission_bps=7.0,
        slippage_bps=2.5,
        total_return_pct=10.0,
        annualized_return_pct=12.0,
        annualized_volatility_pct=20.0,
        sharpe=0.6,
        max_drawdown_pct=-15.0,
        compare_snapshot={
            "symbol": "MSFT",
            "latest_close": 321.0,
            "latest_rsi": 60.0,
            "latest_regime": "bull",
            "period_return_pct": 25.0,
        },
    )

    assert "# Research Report — AAPL" in text
    assert "## Objective" in text
    assert "## Data Window" in text
    assert "## Indicator Snapshot" in text
    assert "## Backtest Summary" in text
    assert "## Risk Notes" in text
    assert "## Final Recommendation" in text
    assert "Relative Return vs Benchmark" in text


def test_build_research_report_markdown_omits_compare_section_when_missing():
    text = build_research_report_markdown(
        symbol="AAPL",
        start_date="2024-01-01",
        end_date="2024-12-31",
        rows_analyzed=100,
        latest_close=123.45,
        latest_rsi=55.1,
        latest_regime="bull",
        commission_bps=5.0,
        slippage_bps=3.0,
        total_return_pct=10.0,
        annualized_return_pct=12.0,
        annualized_volatility_pct=20.0,
        sharpe=0.6,
        max_drawdown_pct=-15.0,
        compare_snapshot=None,
    )

    assert "Relative Return vs Benchmark" not in text
