FROM python:3.12-slim

WORKDIR /srv/backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY apps/backend/pyproject.toml ./
RUN pip install --no-cache-dir .

COPY apps/backend/ ./
RUN pip install --no-cache-dir --no-deps .

COPY infra/docker/backend-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["api"]
