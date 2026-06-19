#!/usr/bin/env python3
"""Generate TypedDict parameter classes from Google API method schemas.

Reads method YAML files and generates typed parameter definitions for use
in service builder methods.

Usage:
    # Generate TypedDict for all Gmail methods
    python typed_params.py gmail
    
    # Generate for specific methods
    python typed_params.py gmail --methods send get list
    
    # Output to custom location
    python typed_params.py gmail --output ../../clients/google_client_v2/params/gmail.py
"""

from pathlib import Path
import yaml
from typing import Any

# TODO: Implement TypedDict generation from method YAML schemas
# This will read files like:
#   ../gmail/methods/users/messages/send.yaml
#   ../gmail/methods/users/messages/get.yaml
# And generate:
#   class SendMessageParams(TypedDict):
#       userId: str
#       body: dict[str, Any]
#   
#   class GetMessageParams(TypedDict):
#       userId: str
#       id: str
#       format: NotRequired[Literal["minimal", "full", "raw", "metadata"]]
#       metadataHeaders: NotRequired[list[str]]

def main():
    print("TypedDict generation not yet implemented.")
    print("See _tooling/README.md for manual Pydantic generation workflow.")

if __name__ == "__main__":
    main()
