FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set the working directory
WORKDIR /app

# Install system dependencies, Git and build essentials
RUN apt-get update && \
    apt-get install -y curl build-essential git cmake

# Install uv
RUN pip install uv

# Copy poetry files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv pip install -e .

# Copy the application code
COPY . .

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Command to run your application
CMD ["python", "app.py"]
