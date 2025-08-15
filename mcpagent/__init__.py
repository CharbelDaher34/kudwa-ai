import argparse
import logging

from .server import (

    mcp,
)



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
