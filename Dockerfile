FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PPGCA_DATABASE=/app/data/ppgca.sqlite3
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer fonts-liberation fontconfig && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY app.py db.py documents.py pdf_template.py setup.py iniciar.py backup.py ./
COPY assets/ ./assets/
COPY templates/ ./templates/
COPY static/ ./static/
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000","--proxy-headers"]
