# Tracked Objects Watchlist — R0.4

## Meaning of “tracked”

**Tracked** means saved locally in your watchlist for manual recall. It does **not** mean continuous background monitoring, push notifications, or cloud sync.

Entries are refreshed only when you request it (or when you select an entry and use refresh while the app is open).

## Storage location

| Item | Path |
|------|------|
| Authoritative file | `{project_root}/runtime_data/tracked_objects.json` |
| Backup before replace | `{project_root}/runtime_data/tracked_objects.json.bak` |
| Optional browser cache | `localStorage` key `foxai_stellar_cartography_watchlist_cache_v1` (not authoritative) |

`runtime_data/` is excluded from release ZIPs and checksum manifests.

## Schema (version 1)

```json
{
  "schema_version": 1,
  "entries": [
    {
      "watchlist_id": "wl_...",
      "display_name": "...",
      "normalized_object_type": "...",
      "source_identifier": null,
      "saved_ra_deg": 0.0,
      "saved_dec_deg": 0.0,
      "coordinate_source": "stellarium|manual|featured_tracker",
      "date_added": "ISO-8601 UTC",
      "last_refreshed": null,
      "favorite": false,
      "personal_note": "",
      "featured_kind": null,
      "provider_identifiers": {}
    }
  ]
}
```

`featured_kind: "apophis"` marks the optional Apophis tracker entry.

## Duplicate handling

Deterministic merge key (first match wins, incoming merges into existing):

1. `source_identifier` when present (case-insensitive)
2. `featured:apophis` for the Apophis featured entry
3. Otherwise `(normalized_object_type, saved_ra_deg, saved_dec_deg)` rounded to **4** decimal places

## Atomic write and recovery

1. Valid previous file copied to `.bak`
2. New JSON written to a temp file in `runtime_data/`
3. Atomic `os.replace()` to `tracked_objects.json`
4. On load failure: attempt restore from `.bak`
5. If both fail: return empty document (schema version 1)

Notes are plain text only; control characters stripped. No executable content.

## Performance

Automated tests verify 100 entries remain responsive and cause **no automatic mass network requests**.

## Exclusions (R0.4)

- No Starlink tracking
- No general artificial-satellite tracking
- No online account or cloud database
