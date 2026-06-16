# LexFeed API — built for Hugging Face Spaces (Docker SDK).
# Moved here from Render because loading sentence-transformers/torch needs
# more than Render's free 512MB RAM; HF Spaces' free CPU tier gives ~16GB.

FROM python:3.10-slim

WORKDIR /app

# build-essential is needed for a couple of ML wheels with no prebuilt
# binary for slim images; removed again after pip install to keep the
# final image smaller.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Hugging Face Spaces (Docker SDK) routes traffic to port 7860 by convention.
EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
