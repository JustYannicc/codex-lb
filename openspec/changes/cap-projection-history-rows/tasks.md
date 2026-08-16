## 1. Implementation

- [x] 1.1 Add a newest-first per-account row cap to the PostgreSQL bulk
      usage-history read (lateral top-N probe per account, composed with the
      existing per-account cutoffs; oldest-first slices preserved).
- [x] 1.2 Pass the cap from the dashboard projections history fetch, sized
      so EWMA depletion, weekly-pace burn, and pace smoothing see identical
      inputs at supported sample cadences.
- [x] 1.3 Keep the SQLite snapshot-cache path on the shared floor (cap
      ignored, like cutoffs).

## 2. Validation

- [x] 2.1 Regression: capped slices equal the newest rows of the uncapped
      fetch, compose with per-account cutoffs, and leave under-cap accounts
      untouched; SQLite ignores the cap.
- [x] 2.2 PostgreSQL plan test: the capped lateral probes stay index-only on
      the covering indexes.
- [x] 2.3 Unit test: the projections fetch supplies the cap.
- [x] 2.4 Run lint, type checks, sqlite + PostgreSQL test slices, and strict
      OpenSpec validation.
