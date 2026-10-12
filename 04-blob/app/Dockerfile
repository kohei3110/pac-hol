FROM mcr.microsoft.com/azurelinux/base/python@sha256:d1a693353b7db0383e66a61416a049f617fdfb89435dcaac543749fb4f14950a

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    HOME=/tmp

WORKDIR /opt/blob-viz
COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt
COPY gunicorn.conf.py ./
COPY blob_viz ./blob_viz
USER 10001:10001
EXPOSE 8080
CMD ["python3", "-m", "gunicorn", "--config", "gunicorn.conf.py", "blob_viz:create_app()"]
