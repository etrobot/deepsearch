# Use the official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.cargo/bin:${PATH}"

# Set the working directory
WORKDIR /app

# Install system dependencies, Rust and Git
RUN apt-get update && \
    apt-get install -y curl build-essential git cmake && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . $HOME/.cargo/env

# Verify Rust installation
RUN cargo --version

# Install poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Install dependencies using poetry
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Copy the application code
COPY . .

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Command to run your application
CMD ["python", "app.py"]
