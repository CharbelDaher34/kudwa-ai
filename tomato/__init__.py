import argparse
import logging

from .server import (
    get_tables,
    describe_table,
    filter_table_names,
    execute_query,
    query_database,
    mcp,
)

# Optionally expose other important items at package level
__all__ = [
    "get_tables",
    "describe_table",
    "filter_table_names",
    "execute_query",
    "query_database",
]


def main():
    parser = argparse.ArgumentParser(description="MCP SQLAlchemy Server")
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "sse"],
        help="Transport mode: stdio or sse",
    )

    args = parser.parse_args()
    logging.info(f"Starting server with transport={args.transport} ")
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
