# pandas profile

Use for pandas major/minor upgrades, especially 1.x -> 2.x. Minor bumps within 2.x may only need deprecation-related searches.

## Common risks

- dtype inference changes (e.g., `object` → `string`, int → `Int64` nullable)
- nullable dtype behavior (NA propagation differences)
- datetime parsing default assumptions changed
- `groupby` / `agg` / `merge` edge-case behavior changes
- `merge`/`join` null-key handling differences
- `read_csv` / `read_excel` encoding, dtype, and column inference changes
- removed deprecated methods: `append`, `ix`, `iteritems`
- `inplace=True` no longer copies (Copy-on-Write in 3.0)
- `resample`, `rolling` API changes or deprecations
- `dropna`, `fillna` default behavior shifts

## Searches

```bash
rg -n "read_csv|read_excel|to_datetime|to_numeric" .
rg -n "\.astype\b|\.fillna\b|\.dropna\b|\.drop_duplicates\b" .
rg -n "\.groupby\b|\.agg\b|\.merge\b|\.join\b|\.concat\b" .
rg -n "\.append\b|\.ix\[|\.iteritems\b" .
rg -n "\.sort_values\b|\.pivot_table\b|\.resample\b|\.rolling\b" .
rg -n "inplace=True|infer_objects" .
rg -n "copy=True|copy=False" .
rg -n "Int64Dtype|StringDtype|BooleanDtype|Float64Dtype" .
```

## Smoke tests

- read representative input file with explicit dtype expectations
- preserve expected dtypes for key columns (numeric, datetime, string)
- null/empty/date edge cases in aggregation and merge
- groupby/merge output row counts match expectations
- serialization output shape and column names preserved
- `append`-style operations migrated to `pd.concat`
- timezone-aware datetime handling correctness

## Version awareness

This profile is most relevant for 1.x -> 2.x upgrades where dtype inference and deprecated method removals have the biggest impact. Minor bumps within 2.x may only need deprecation-related searches; correlate the search patterns to the exact version jump in the alert.
