# Draining-owner recovery

This local integration reconstructs PR2088 on upstream main f1ff7c7c3. The
forwarding client reports non-200 receiver rejection through its callback;
that transport evidence controls recovery. An error code is insufficient
because the same payload can follow an ambiguous or acknowledged dispatch.

For example, a signed owner-forward request receives HTTP 503 with
`bridge_drain_active`. The origin releases the rejected request's reservation
before admitting a local replacement. A file reference still pins the
replacement to its existing account. If the origin cannot release the old
reservation, it fails before creating the replacement attempt.

The fix stays in the existing large bridge modules because outcome tracking,
recovery admission, and reservation lifecycle already live at these call sites.
Extracting them for this patch would move unrelated bridge state.
