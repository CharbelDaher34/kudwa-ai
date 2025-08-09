import json
import sys
from typing import Any

def print_schema(data: Any, indent: int = 0):
    """Recursively print JSON structure."""
    prefix = "  " * indent
    if isinstance(data, dict):
        for key, value in data.items():
            print(f"{prefix}{key}: {type(value).__name__}")
            print_schema(value, indent + 1)
    elif isinstance(data, list):
        print(f"{prefix}list[{len(data)}]")
        if data:
            print_schema(data[0], indent + 1)
    else:
        pass  # Base case: already printed type

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <json_file>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        json_data = json.load(f)

    print_schema(json_data)
