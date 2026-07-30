# AlphaForge Web Terminal UI

This is the new browser-based interface for AlphaForge. It intentionally keeps
the existing Python quant engine untouched while establishing the visual and
interaction system for the migration away from PySide6.

## Preview

From the repository root:

```bash
python -m http.server 8080 --directory web
```

Then open `http://localhost:8080`.

## Product direction

- Market and portfolio data are the primary product.
- AI is available only through the collapsible Copilot rail.
- Visual depth is created with restrained perspective, lighting, glass layers,
  and motion.
- Motion respects `prefers-reduced-motion`.
- Current values are design fixtures and will be replaced by API responses from
  the existing Python services.

## Next integration boundary

Expose the Python service layer through a small HTTP/WebSocket API:

- `GET /api/market/{symbol}`
- `GET /api/watchlist`
- `POST /api/backtests`
- `POST /api/portfolios/risk`
- `POST /api/copilot`
- `WS /api/stream/quotes`
