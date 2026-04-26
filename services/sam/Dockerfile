FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "fastapi>=0.110,<1.0" \
    "uvicorn[standard]>=0.27,<1.0" \
    "pillow>=10.4,<12.0" \
    "numpy>=1.26,<3.0" \
    "torch==2.4.1+cpu" --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir \
    "transformers>=4.44,<5.0" \
    "huggingface-hub>=0.24,<1.0"

ENV HF_HOME=/models/hf
ENV TRANSFORMERS_CACHE=/models/hf
ENV ARTPIPE_SAM_MODEL=facebook/sam-vit-base

RUN python -c "import os; from transformers import SamModel, SamProcessor; m=os.environ['ARTPIPE_SAM_MODEL']; SamModel.from_pretrained(m); SamProcessor.from_pretrained(m)"

COPY server.py /app/server.py

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
