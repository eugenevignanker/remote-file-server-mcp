import datetime
import json
import logging
import logging.handlers
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)

# Silence noisy third-party loggers
for _noisy in ("mcp", "fastmcp", "smbprotocol", "smbclient", "spnego", "ntlm"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

log = logging.getLogger("file-server-mcp")

# Audit logger writes one JSON object per line, never file contents.
_audit_logger = logging.getLogger("file-server-mcp.audit")
_audit_logger.setLevel(logging.INFO)
_audit_logger.propagate = False  # don't double-emit to the root handler

AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "").strip()
if AUDIT_LOG_PATH:
    _audit_handler: logging.Handler = logging.handlers.WatchedFileHandler(
        AUDIT_LOG_PATH, encoding="utf-8"
    )
else:
    _audit_handler = logging.StreamHandler(sys.stderr)

_audit_handler.setFormatter(logging.Formatter("%(message)s"))
_audit_logger.addHandler(_audit_handler)


def audit(operation: str, path: str, outcome: str, **extra: object) -> None:
    """Emit a single JSON audit log entry. Never include file contents."""
    record: dict[str, object] = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operation": operation,
        "path": path,
        "outcome": outcome,
    }
    record.update(extra)
    _audit_logger.info(json.dumps(record, default=str))
