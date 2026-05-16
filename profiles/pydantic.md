# Pydantic profile

Use for Pydantic 1.x -> 2.x and FastAPI-adjacent model validation changes.

## Common risks

- `parse_obj`, `parse_raw`, `dict`, `json` replacements or behavior changes
- validator/root_validator migration
- changed alias/population behavior
- stricter/laxer validation defaults
- changed serialization of dates, enums, decimals, optional fields
- BaseSettings moved to pydantic-settings

## Searches

```bash
rg -n "BaseModel|BaseSettings|parse_obj|parse_raw|parse_file" .
rg -n "\.dict\(|\.json\(|model_dump|model_validate" .
rg -n "@validator|@root_validator|field_validator|model_validator" .
rg -n "allow_population_by_field_name|populate_by_name|orm_mode|from_attributes" .
```

## Smoke tests

- parse representative payload
- reject invalid payload that should fail
- serialize model to API/DB format
- check aliases/defaults/nulls/enums/datetimes
- run FastAPI route schema generation if applicable
