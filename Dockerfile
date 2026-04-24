FROM mcr.microsoft.com/playwright/python:v1.52.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY run_bot.py .
COPY spot_bot/ spot_bot/

# Mount points for the docker-compose named volumes. Creating them here
# means the container can start cleanly even before the volumes are
# populated, and Docker won't need to root-own them.
RUN mkdir -p /app/data /app/logs

CMD ["python", "run_bot.py"]
