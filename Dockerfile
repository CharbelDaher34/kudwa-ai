FROM python:3.13-slim

# Copy the uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml .
COPY uv.lock .

# Create virtual environment and install packages
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies and sync the virtual environment
RUN uv venv && \
    uv lock && \
    uv sync --locked

# Copy application files
COPY . .

# Make run_all.sh executable
RUN chmod +x run_all.sh

CMD ["./run_all.sh"] 