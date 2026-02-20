FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG DEBIAN_FRONTEND=noninteractive
ARG INSTALL_PREVIEW_SDKS=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       git \
       unzip \
       xz-utils \
       nodejs \
       npm \
    && rm -rf /var/lib/apt/lists/*

RUN if [ "${INSTALL_PREVIEW_SDKS}" = "1" ]; then \
      git clone --depth 1 -b stable https://github.com/flutter/flutter.git /opt/flutter; \
    fi

ENV FLUTTER_HOME=/opt/flutter
ENV PATH=/opt/flutter/bin:/opt/flutter/bin/cache/dart-sdk/bin:$PATH

RUN if [ "${INSTALL_PREVIEW_SDKS}" = "1" ]; then \
      ln -sf /opt/flutter/bin/flutter /usr/local/bin/flutter; \
      ln -sf /opt/flutter/bin/dart /usr/local/bin/dart; \
    fi

RUN if [ "${INSTALL_PREVIEW_SDKS}" = "1" ]; then \
      flutter --version; \
    fi

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY rebot /app/rebot
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md

WORKDIR /app/backend
ENV PYTHONPATH=/app:/app/backend

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
