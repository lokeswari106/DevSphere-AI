FROM node:22-bookworm-slim AS node
WORKDIR /deps
RUN npm install --ignore-scripts --no-audit --no-fund express@5.1.0 supertest@7.1.4
FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends default-jdk-headless && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /runner/requirements.txt
RUN pip install --no-cache-dir -r /runner/requirements.txt
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /deps/node_modules /deps/node_modules
COPY run.py /runner/run.py
RUN mkdir /input && chmod 755 /input
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NODE_PATH=/deps/node_modules
USER 65532:65532
WORKDIR /workspace
ENTRYPOINT ["python", "/runner/run.py"]
