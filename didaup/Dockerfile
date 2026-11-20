FROM python:3.12-slim-bookworm
WORKDIR /srv/didaup
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt /srv/didaup/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r /srv/didaup/requirements.txt \
    && groupadd --system didaup \
    && useradd --system --gid didaup --home /srv/didaup didaup
COPY app /srv/didaup/app
COPY run.sh /run.sh
RUN chmod 755 /run.sh && mkdir -p /data && chown didaup:didaup /data
EXPOSE 8097
CMD ["/run.sh"]
