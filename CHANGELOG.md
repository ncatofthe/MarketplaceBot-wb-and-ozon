# CHANGELOG - MarketplaceBot

## [v1.1.0] - 2026-03-16 - BLACKBOXAI Fixes

### ✨ **Major Improvements**
- **Ozon Bot Full Fix**: v1/review API (list/info/comment), pagination, correct rating/text parsing (direct result.rating=1/5), fallback 5, rate-limit sleep.
- **163 UNPROCESSED reviews processed/answered** (tested).
- **Rating-based templates**: 1* apologies, 5* thanks - logs show raw vs parsed rating + full answer text.

### 🐛 **Bug Fixes**
- Parsing: `result_info = info.get('result', {}) or info`, `rating = int(raw_rating) or 5`.
- base_bot fallback `stars = review.get("rating") or 5`.
- Detailed logs: raw Ozon rating/type/keys, generated answer preview.

### 📝 **Docs Updated**
- ИНСТРУКЦИЯ.md: API setup, test commands (`python test_ozon_full.py`).
- README.md: Installation, usage, structure.
- ИСПРАВЛЕНИЯ.md: Added Ozon API migration, tests.

### ✅ **Tests**
- `test_all.py`: FULL SUCCESS (imports/config/answers/bots).
- `test_ozon_full.py`: Connect → 163 found → all answered with logs.

## [v1.0.0] - Initial

Bot for auto-replying to marketplace reviews.
