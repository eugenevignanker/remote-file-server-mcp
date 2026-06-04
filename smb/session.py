import sys

import smbclient

from config import SMB_HOST, SMB_PORT, SMB_USERNAME, SMB_PASSWORD, SMB_SHARE, SMB_ENCRYPT, SMB_DOMAIN
from smb.helpers import SHARE_ROOT_UNC
from utils.logger import log


def setup() -> None:
    username = fr"{SMB_DOMAIN}\{SMB_USERNAME}" if SMB_DOMAIN else SMB_USERNAME
    smbclient.register_session(
        SMB_HOST,
        username=username,
        password=SMB_PASSWORD,
        port=SMB_PORT,
        require_signing=True,
        encrypt=SMB_ENCRYPT,
    )
    _check_connection()


def _check_connection() -> None:
    """
    Probe the share root to confirm the SMB connection and credentials are valid.
    Exits the process with a clear error message if the server is unreachable or
    authentication fails.
    """
    share_root = SHARE_ROOT_UNC
    try:
        smbclient.scandir(share_root)
        log.info("SMB session ready — connected to %s", share_root)
    except Exception as exc:
        exc_type = type(exc).__name__
        if "LogonFailure" in exc_type or "AccessDenied" in exc_type:
            log.error(
                "SMB authentication failed. Check SMB_USERNAME, SMB_PASSWORD, and SMB_DOMAIN if set. (%s)",
                exc_type,
            )
        elif "ConnectionRefused" in exc_type or "Timeout" in exc_type or "NoSuchServer" in exc_type:
            log.error(
                "Cannot reach SMB server at %s:%d. Check SMB_HOST and SMB_PORT. (%s)",
                SMB_HOST, SMB_PORT, exc_type,
            )
        elif "ObjectNotFound" in exc_type or "BadNetworkName" in exc_type:
            log.error(
                "SMB share or subfolder not found. Check SMB_SHARE and SMB_SUBFOLDER. (%s)", exc_type,
            )
        else:
            log.error("SMB connection check failed: %s — %s", exc_type, exc)
        sys.exit(1)
