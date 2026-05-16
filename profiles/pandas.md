# pandas profile

Use for pandas major/minor upgrades, especially 1.x -> 2.x.

## Common risks

- dtype inference changes
- nullable dtype behavior
- datetime parsing changes
- groupby/aggregation edge cases
- merge/join null-key behavior assumptions
- CSV/Excel IO behavior
- removed deprecated methods such as `append`

## Searches

```bash
rg -n "read_csv|read_excel|to_datetime|astype|fillna|infer_objects" .
rg -n "groupby|agg\(|merge\(|join\(|concat\(" .
rg -n "\.append\(|iteritems\(|ix\[" .
rg -n "drop_duplicates|sort_values|pivot_table|resample" .
```

## Smoke tests

- read representative input file
- preserve expected dtypes for key columns
- null/empty/date edge cases
- groupby/merge output row counts
- serialization output shape and column names
