"""Generated Pydantic models from Google API schemas (reference only).

These files serve as comprehensive reference. Active workflows extract
focused models to shared_utilities/clients/google_client_v2/models/.

Extracted models:
    - Message, SendAs (gmail) → google_client_v2/models/

When the monolith references extracted models, they are re-imported
to maintain backward compatibility.

Regeneration command:
    python3 scripts/google_api/consolidate_schemas.py
    # Then for each API:
    datamodel-codegen \
      --input /tmp/consolidated_schemas/{api}.yaml \
      --output shared_utilities/generated_models/google/{api}.py \
      --input-file-type jsonschema \
      --output-model-type pydantic_v2.BaseModel \
      --use-schema-description \
      --use-field-description \
      --field-constraints \
      --use-annotated \
      --snake-case-field
"""
