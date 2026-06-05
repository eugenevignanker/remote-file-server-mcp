import os
import posixpath
import sys

from utils.logger import log

_REQUIRED_ENV = ["SMB_HOST", "SMB_SHARE", "SMB_USERNAME", "SMB_PASSWORD"]
_missing = [v for v in _REQUIRED_ENV if not os.environ.get(v)]
if _missing:
    log.error("Missing required environment variables: %s", ", ".join(_missing))
    sys.exit(1)

SMB_HOST = os.environ["SMB_HOST"]
SMB_PORT = int(os.environ.get("SMB_PORT", "445"))
SMB_DOMAIN = os.environ.get("SMB_DOMAIN")
SMB_USERNAME = os.environ["SMB_USERNAME"]
SMB_PASSWORD = os.environ["SMB_PASSWORD"]
SMB_SHARE = os.environ["SMB_SHARE"]
_raw_subfolder = os.environ.get("SMB_SUBFOLDER", "").strip().replace("\\", "/").strip("/")
SMB_SUBFOLDER = "" if not _raw_subfolder else posixpath.normpath(_raw_subfolder).lstrip("/")
if SMB_SUBFOLDER.startswith(".."):
    log.error("Invalid SMB_SUBFOLDER: must stay within the configured share.")
    sys.exit(1)
SMB_ENCRYPT = os.environ.get("SMB_ENCRYPT", "false").lower() == "true"
MAX_FILE_SIZE_BYTES = int(os.environ.get("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024
READ_PREVIEW_LINES = int(os.environ.get("READ_PREVIEW_LINES", "100"))

log.info(
    "Startup configuration: SMB_HOST=%r SMB_PORT=%d SMB_SHARE=%r SMB_SUBFOLDER=%r "
    "SMB_DOMAIN=%r SMB_USERNAME=%r SMB_ENCRYPT=%r MAX_FILE_SIZE_MB=%d "
    "READ_PREVIEW_LINES=%d ALLOWED_PATHS=%r AUDIT_LOG_PATH=%r",
    SMB_HOST,
    SMB_PORT,
    SMB_SHARE,
    SMB_SUBFOLDER,
    SMB_DOMAIN,
    SMB_USERNAME,
    SMB_ENCRYPT,
    MAX_FILE_SIZE_BYTES // (1024 * 1024),
    READ_PREVIEW_LINES,
    os.environ.get("ALLOWED_PATHS", ""),
    os.environ.get("AUDIT_LOG_PATH", ""),
)
