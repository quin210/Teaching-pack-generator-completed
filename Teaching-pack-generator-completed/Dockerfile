# FROM python:3.12-slim

# WORKDIR /app

# # system deps (tuy ban dung pdf2image/pytesseract)
# RUN apt-get update && apt-get install -y \
#     poppler-utils \
#     tesseract-ocr \
#     && rm -rf /var/lib/apt/lists/*

# COPY pyproject.toml /app/
# COPY src /app/src
# COPY run_server.py /app/
# COPY run_worker.py /app/

# RUN pip install --no-cache-dir -U pip setuptools wheel
# RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
# RUN pip install --no-cache-dir -e .

# EXPOSE 8000

# CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "api.main:app", "--bind", "0.0.0.0:8000"]
FROM python:3.12-slim

WORKDIR /app

# system deps (tuy ban dung pdf2image/pytesseract)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
COPY src /app/src
COPY run_server.py /app/
COPY run_worker.py /app/

RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "api.main:app", "--bind", "0.0.0.0:8000"]
CMD ["gunicorn","api.main:app","-k","uvicorn.workers.UvicornWorker","--workers","1","--timeout","300","--graceful-timeout","30","--keep-alive","75","--bind","0.0.0.0:8000","--access-logfile","-","--error-logfile","-","--log-level","info"]

