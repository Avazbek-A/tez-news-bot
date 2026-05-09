FROM python:3.12-slim-bookworm

WORKDIR /app

# ffmpeg is needed to convert TTS mp3 output into Opus/OGG so audio can
# be sent as Telegram voice messages (which support mobile speed control).
# build-essential is only present briefly to compile selectolax's C
# extension wheel on architectures without prebuilt wheels; we strip
# it back out to keep the image small.
RUN set -eux; \
    apt-get update -o Acquire::Retries=3; \
    apt-get install -y --no-install-recommends ffmpeg ca-certificates; \
    rm -rf /var/lib/apt/lists/*; \
    ffmpeg -version

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY run_bot.py .
COPY spot_bot/ spot_bot/

CMD ["python", "run_bot.py"]
