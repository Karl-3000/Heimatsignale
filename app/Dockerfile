FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home --uid 10001 heimat
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN mkdir -p /data/journal /data/static && chown -R heimat /data
USER heimat
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "heimatsignale.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--access-logformat", "%(m)s %(U)s %(s)s %(M)sms"]
