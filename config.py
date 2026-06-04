import os
import sys

from utils.logger import log

_REQUIRED_ENV = ["SMB_HOST", "SMB_SHARE", "SMB_DOMAIN", "SMB_USERNAME", "SMB_PASSWORD"]
_missing = [v for v in _REQUIRED_ENV if not os.environ.get(v)]
if _missing:
    log.error("Missing required environment variables: %s", ", ".join(_missing))
    sys.exit(1)

SMB_HOST = os.environ["SMB_HOST"]
SMB_PORT = int(os.environ.get("SMB_PORT", "445"))
SMB_DOMAIN = os.environ["SMB_DOMAIN"]
SMB_USERNAME = os.environ["SMB_USERNAME"]
SMB_PASSWORD = os.environ["SMB_PASSWORD"]
SMB_SHARE = os.environ["SMB_SHARE"]
SMB_ENCRYPT = os.environ.get("SMB_ENCRYPT", "false").lower() == "true"
MAX_FILE_SIZE_BYTES = int(os.environ.get("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024
READ_PREVIEW_LINES = int(os.environ.get("READ_PREVIEW_LINES", "100"))
