# Use CPU-only torch image — smaller than full CUDA image.
# If you need GPU, change base to: pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime
FROM python:3.11-slim

WORKDIR /app

# System deps for torch / scipy / scikit-learn native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# --- Install PyTorch CPU-only first (avoids pulling CUDA wheels) ---
RUN pip install --no-cache-dir \
    torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu

# --- torch-geometric requires separate channel ---
RUN pip install --no-cache-dir \
    torch-scatter torch-sparse torch-cluster torch-spline-conv \
    -f https://data.pyg.org/whl/torch-2.4.1+cpu.html

# --- Rest of requirements (skip torch lines to avoid re-download) ---
COPY requirements.txt .
RUN grep -v "^torch" requirements.txt | pip install --no-cache-dir -r /dev/stdin

# Copy source + pre-trained artifacts
COPY ml/ ./ml/
COPY artifacts/ ./artifacts/
COPY configs/ ./configs/
COPY data/ ./data/

# Expose ML server port
EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8081/health || exit 1

# Run as module so relative imports (ml.config, ml.model…) resolve correctly
CMD ["python", "-m", "ml.serving.prediction_server"]
