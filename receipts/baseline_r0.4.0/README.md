# R0.4.0 baseline receipt quarantine

These files are the **immutable R0.4.0 release artifacts**, moved here
byte-for-byte from the repository root when R0.5.0 development began.

| File | Role |
|------|------|
| `BUILD_RECEIPT_R0.4.0.json` | Final R0.4.0 build receipt (unchanged content) |
| `SHA256SUMS_R0.4.0.txt` | File checksums from the R0.4.0 freeze |

## Important

- The paths listed inside `SHA256SUMS_R0.4.0.txt` are **relative to the
  original R0.4.0 archive layout** (e.g. `BUILD_RECEIPT.json` at the archive
  root). They are **historical evidence** of that release, not a current
  manifest for this R0.5.0 working tree.
- Do **not** rewrite these files to describe R0.5.0 development.
- Do **not** treat them as the active build receipt for this workspace.
- A uniquely versioned R0.5.0 receipt and checksum set will be created only
  at final packaging time.

## Integrity

Moved with `git mv` and verified SHA-256-identical to the pre-move root
copies before the quarantine commit.
