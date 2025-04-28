FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install basic system dependencies (only what's necessary for pip and system)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy app files
COPY . .

# Install Python packages (headless OpenCV saves space!)
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose Flask port
EXPOSE 5000

# Command to run
CMD ["python", "app.py"]