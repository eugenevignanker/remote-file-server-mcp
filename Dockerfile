# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# file-server-mcp — MCP server for SMB/CIFS file share access
#
# Build:
#   docker build -t file-server-mcp .
#
# Run (inject secrets at runtime — NEVER bake them into the image):
#   docker run --rm -i \
#     -e SMB_HOST=192.168.1.100 \
#     -e SMB_SHARE=my_share \
#     -e SMB_USERNAME=my_user \
#     -e SMB_PASSWORD=my_password \
#     -e SMB_DOMAIN=MYDOMAIN \
#     file-server-mcp
#
# Or use --env-file to keep secrets out of shell history:
#   docker run --rm -i --env-file .env file-server-mcp
#
# Optional env vars: SMB_DOMAIN, SMB_PORT, SMB_ENCRYPT, MAX_FILE_SIZE_MB,
#                    ALLOWED_PATHS, AUDIT_LOG_PATH, READ_PREVIEW_LINES
# ---------------------------------------------------------------------------

FROM python:3.12-slim AS builder

WORKDIR /app

# Copy the full package source (pyproject.toml must be present for pip install)
COPY pyproject.toml README.md ./
COPY server.py config.py ./
COPY smb/ smb/
COPY tools/ tools/
COPY utils/ utils/

# Build the installed runtime into a separate prefix so the final stage can
# copy only the artifacts needed to run the server.
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --prefix /install .

FROM python:3.12-slim AS runtime

# Create a non-root user — never run the server as root
RUN useradd --create-home --shell /bin/bash mcpuser

WORKDIR /app

# Collapse the build output into the runtime image without carrying the full
# source tree or build tooling forward.
COPY --from=builder /install /usr/local

# MCP servers communicate over stdio — no ports to expose
# Secrets must be injected via environment variables at runtime
ENV SMB_PORT=445 \
    SMB_ENCRYPT=false \
    MAX_FILE_SIZE_MB=10 \
    READ_PREVIEW_LINES=100

USER mcpuser

ENTRYPOINT ["file-server-mcp"]
    
