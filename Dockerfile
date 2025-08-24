FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy pyproject.toml and uv.lock for dependency installation
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install uv
RUN uv sync

# Copy application files
COPY app.py ./
COPY models.py ./
COPY setup.py ./
COPY templates/ ./templates/
COPY static/ ./static/

# Expose port
EXPOSE 5001

# Run the Flask application
CMD ["uv", "run", "python", "app.py"]
