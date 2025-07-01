FROM python:3.12-slim

# install system deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git build-essential nodejs npm supervisor \
 && npm install -g yarn \
 && rm -rf /var/lib/apt/lists/*

# install Gixy
WORKDIR /opt/gixy
RUN git clone --depth 1 https://github.com/MegaManSec/gixy.git . \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir .

# install FastAPI deps
RUN pip install --no-cache-dir fastapi==0.111.0 uvicorn==0.30.0 python-multipart==0.0.9

# install ReCheck
WORKDIR /opt/recheck-http-api
RUN git clone --depth 1 https://github.com/MegaManSec/recheck-http-api.git . \
 && yarn install --frozen-lockfile && yarn bootstrap

# copy your FastAPI app
WORKDIR /opt/app
COPY app.py .

# overwrite the default Supervisor config
COPY supervisord.conf /etc/supervisor/supervisord.conf

# drop root, run as worker
RUN useradd -m worker
USER worker

EXPOSE 8080
ENTRYPOINT ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
