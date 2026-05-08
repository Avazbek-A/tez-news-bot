FROM mcr.microsoft.com/playwright/python:v1.52.0-noble

WORKDIR /app

# ffmpeg is needed to convert TTS mp3 output into Opus/OGG so audio can
# be sent as Telegram voice messages (which support mobile speed control).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY run_bot.py .
COPY spot_bot/ spot_bot/

CMD ["python", "run_bot.py"]
