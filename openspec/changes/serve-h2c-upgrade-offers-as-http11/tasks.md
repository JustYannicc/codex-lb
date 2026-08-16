## 1. Implementation

- [x] 1.1 Neutralize non-WebSocket upgrade offers in the httptools HTTP
      protocol: replay the request head without the declined offer's
      hop-by-hop headers and serve the request as plain HTTP/1.1.
- [x] 1.2 Wire the tolerant protocol into the server bootstrap, falling back
      to uvicorn's `auto` selection (h11 already behaves correctly) when
      httptools is unavailable.

## 2. Validation

- [x] 2.1 Add transport-level regressions: h2c offer with coalesced
      header/body and with split segments both reach the application with the
      full body and succeed; the declined offer's headers are not exposed; the
      connection stays reusable.
- [x] 2.2 Add a live-server regression over real sockets using the production
      protocol wiring, including a real WebSocket upgrade that must keep
      completing, plus a canary pinning the stock uvicorn defect.
- [x] 2.3 Run focused tests, lint, type checks, and strict OpenSpec
      validation.
