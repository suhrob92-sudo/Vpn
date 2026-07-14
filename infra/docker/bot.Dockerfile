FROM python:3.12-slim

WORKDIR /srv/bot
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY apps/bot/pyproject.toml ./
RUN pip install --no-cache-dir .

COPY apps/bot/ ./
RUN pip install --no-cache-dir --no-deps .

CMD ["python", "-m", "bot.main"]
