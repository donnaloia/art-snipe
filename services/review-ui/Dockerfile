FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "fastapi>=0.110,<1.0" \
    "uvicorn[standard]>=0.27,<1.0" \
    "jinja2>=3.1,<4.0" \
    "pydantic>=2.8,<3.0" \
    "python-multipart>=0.0.9,<1.0"

COPY server.py /app/server.py
COPY templates /app/templates

ENV WORKSPACE=/app/workspace
ENV EXPORT_DIR=/app/game_assets

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]
