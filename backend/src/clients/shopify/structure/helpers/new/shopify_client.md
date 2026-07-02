Status: keep
Path: backend/src/clients/shopify/shopify_client.py

Public entry point — thin module that instantiates and re-exports the codegen
`Client` (from `generated/client.py`) with project-configured transport
(`client_base.py`).
