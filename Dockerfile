FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# CPU-only torch first: the default wheel pulls multi-GB CUDA libraries.
RUN pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu     && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV HF_HOME=/app/data/cache/hf \
    SENTENCE_TRANSFORMERS_HOME=/app/data/cache/hf \
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000

EXPOSE 8000 8501

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & streamlit run frontend/app.py --server.address=0.0.0.0 --server.port=8501"]
