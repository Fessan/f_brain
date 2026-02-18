FROM node:20-bookworm-slim AS node

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        gosu \
        openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy only Node.js runtime (not full /usr/local/ to avoid overwriting Python libs)
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Pin uv version for reproducible builds
RUN curl -LsSf https://astral.sh/uv/0.6.0/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

ARG TARGETARCH=amd64
RUN curl -fsSL "https://github.com/aptible/supercronic/releases/download/v0.2.37/supercronic-linux-${TARGETARCH}" \
    -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

RUN npm install -g @anthropic-ai/claude-code
RUN npm install -g @openai/codex

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /home/app/.claude \
    && mkdir -p /home/app/.codex \
    && chown -R app:app /home/app

WORKDIR /app
RUN chown app:app /app

# 1. Dependency files + package stub for editable install (best layer cache)
COPY --chown=app:app pyproject.toml uv.lock README.md ./
COPY --chown=app:app src/d_brain/__init__.py ./src/d_brain/__init__.py

# 2. Install deps as app user (cached unless pyproject.toml/uv.lock change)
USER app
RUN uv sync --frozen --all-groups
USER root

# 3. Source code and config (changes more often)
COPY --chown=app:app src ./src
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app tests ./tests
COPY --chown=app:app deploy ./deploy
COPY --chown=app:app docs ./docs
COPY --chown=app:app mcp-config.json ./
COPY --chown=app:app AGENTS.md QUICKSTART.md PROJECT_NOTES.md STRUCTURE.json tasks.json ./
COPY --chown=app:app vault ./vault

# 4. Git template last (changes on every commit)
COPY --chown=app:app .git ./.git-template

COPY --chown=root:root scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && chown app:app /app

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uv", "run", "python", "-m", "d_brain"]
