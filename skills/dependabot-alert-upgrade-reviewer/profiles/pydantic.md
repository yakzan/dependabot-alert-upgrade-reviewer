# Pydantic profile

Use for Pydantic 1.x -> 2.x and FastAPI-adjacent model validation changes. Patch bumps within 2.x generally do not need the full profile.

## Common risks

- `parse_obj` / `parse_raw` / `parse_file` / `from_orm` removed in v2
- `.dict()` / `.json()` replaced by `model_dump()` / `model_dump_json()`
- `@validator` → `@field_validator`, `@root_validator` → `@model_validator`
- `orm_mode` → `from_attributes`, `allow_population_by_field_name` → `populate_by_name`
- `BaseSettings` moved to `pydantic-settings` package
- `Config` class → `model_config = ConfigDict(...)`
- Changed default validation strictness (lax → strict for some types)
- Changed serialization of dates, enums, decimals, optional fields
- `Field()` parameter changes; `Annotated[type, Field(...)]` preferred style
- `computed_field`, `field_serializer` new in v2

## Searches

```bash
rg -n "BaseModel|BaseSettings|ConfigDict" .
rg -n "parse_obj|parse_raw|parse_file|from_orm" .
rg -n "\.dict\(|\.json\(|model_dump\b|model_dump_json\b" .
rg -n "model_validate\b|model_validate_json\b" .
rg -n "@validator|@root_validator|@field_validator|@model_validator" .
rg -n "field_validator\(|model_validator\(" .
rg -n "allow_population_by_field_name|populate_by_name|orm_mode|from_attributes" .
rg -n "Field\(|Annotated\[|computed_field|field_serializer" .
rg -n "class Config:|model_config" .
```

## Smoke tests

- parse representative payload
- reject invalid payload that should fail
- serialize model to API/DB format with `model_dump`
- JSON round-trip with `model_dump_json` / `model_validate_json`
- check aliases/defaults/nulls/enums/datetimes
- verify deprecated validators produce correct results
- if BaseSettings, confirm `pydantic-settings` is installed
- run FastAPI route schema generation if applicable

## Version awareness

This profile is most relevant for 1.x -> 2.x upgrades where validators, serialization, and settings handling changed significantly. Patch bumps within 2.x generally don't need the full profile; correlate the search patterns to the exact version jump in the alert.
