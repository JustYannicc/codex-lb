# Bounded successor for relay CLOSE and retirement deadline

This local successor starts at frozen `b9997df7ef58721da242a74282535776b30b2eeb`. Its manifest retains all 37 prior source records and 11 repair records, adds PR2315 at `f72cf35b0ce6e94217d20d0b1b1116486012e435`, and records PR2286's bounded repair from `a3b4d42f6` to reviewed `68aa998f12f55c267307b132d29f707209b1059e` as a supplement to the retained original pin.

The relay forwards an omitted CLOSE code as1000, preserving explicit codes and reasons. The detached retirement sweep shares one five-second monotonic lock-wait deadline. For example, after an attempt consumes three seconds, the next gets two; later sessions remain tracked for their cleanup owners. Existing resource-close timing and ownership remain separate.

Composition omits the upstream-only `_usage_payload` fixture type edit because that fixture does not exist in this aggregate. It appends the retirement context without replacing prior ERR/ownership notes. No main refresh, schema revision, identity, projection, routing, ERR repair or other helper change belongs to this successor. PR2303, PR2312 and PR2316 remain excluded from this unit.

The external immutable `reports/composition-2286-2315/receipt.md` binds the candidate, tree, actual event-range OpenSpec validation, affected regression and ownership controls, required checks, independent review and cleanup. Earlier composition receipts remain immutable. Publication, image build and live acceptance belong to the deployment owner; none is established by local source proof.
