FROM mcr.microsoft.com/playwright/python:v1.52.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY run_bot.py .
COPY spot_bot/ spot_bot/

CMD ["python", "run_bot.py"]
