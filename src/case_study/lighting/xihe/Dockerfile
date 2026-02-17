FROM python:3.11-slim

ENV POETRY_VERSION=2.1.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

RUN apt-get update && apt-get install -y curl build-essential && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt-get purge -y --auto-remove curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN poetry install --no-root

# Install additional pip packages
RUN pip install wheel && \
    pip install torch-cluster -f https://data.pyg.org/whl/torch-2.5.0+cpu.html

COPY . .

# Create expected input/output directories
RUN mkdir -p /app/inputs /app/outputs
VOLUME ["/app/inputs", "/app/outputs"]

CMD ["python", "startup.py"]
