FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download MediaPipe pose model at build time
RUN mkdir -p /app/model_cache && \
    curl -sL -o /app/model_cache/pose_landmarker_lite.task \
    https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task

# Download CLIP model at build time (optional – pipeline works without it)
RUN python -c "from transformers import CLIPModel, CLIPProcessor; \
    CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32', cache_dir='/app/model_cache'); \
    CLIPModel.from_pretrained('openai/clip-vit-base-patch32', cache_dir='/app/model_cache')" \
    || echo "CLIP download skipped – reference matching will use fallback"

# Copy application code
COPY app/ app/
COPY reference_data/ reference_data/

# Create data directories
RUN mkdir -p data/uploads data/results data/assets

ENV GOLF_DATA_DIR=/app/data
ENV GOLF_REFERENCE_DIR=/app/reference_data
ENV GOLF_MODEL_CACHE=/app/model_cache
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
