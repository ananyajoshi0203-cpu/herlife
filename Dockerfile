FROM python:3.14-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HERLIFE_WEB_DB=sqlite:////data/herlife_web.db HERLIFE_SECURE_COOKIES=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY web ./web
RUN mkdir -p /data data/raw
EXPOSE 8080
CMD ["sh", "-c", "uvicorn backend.webapp.server:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers"]
