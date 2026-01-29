# Multi-stage build for smaller, more secure images
FROM python:3.10-slim as builder

# Install build dependencies
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.10-slim

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash aroma

# Copy dependencies from builder
COPY --from=builder /root/.local /home/aroma/.local

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=aroma:aroma . /app

# Switch to non-root user
USER aroma

# Add local bin to PATH
ENV PATH=/home/aroma/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python3 -c "import sys; from database import Database; db = Database(); sys.exit(0 if db else 1)" || exit 1

# Run the bot
CMD ["python3", "main.py"]
