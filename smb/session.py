import sys

import smbclient

from config import SMB_HOST, SMB_PORT, SMB_USERNAME, SMB_PASSWORD, SMB_SHARE, SMB_ENCRYPT, SMB_DOMAIN
from smb.helpers import SHARE_ROOT_UNC
from utils.logger import log


def setup() -> None:
    _register_session()
    _check_connection()


def _session_username() -> str:
    return fr"{SMB_DOMAIN}\{SMB_USERNAME}" if SMB_DOMAIN else SMB_USERNAME


def _register_session() -> None:
    username = _session_username()
    smbclient.register_session(
        SMB_HOST,
        username=username,
        password=SMB_PASSWORD,
        port=SMB_PORT,
        require_signing=True,
        encrypt=SMB_ENCRYPT,
    )
    log.info(
        "Registered SMB session for host=%r share=%r user=%r domain=%r",
        SMB_HOST,
        SMB_SHARE,
        SMB_USERNAME,
        SMB_DOMAIN,
    )


def _reset_connection_cache() -> None:
    reset_connection_cache = getattr(smbclient, "reset_connection_cache", None)
    if reset_connection_cache:
        reset_connection_cache()


def _is_retryable_session_error(exc: Exception) -> bool:
    exc_type = type(exc).__name__
    message = str(exc)
    retry_markers = (
        "SMBAuthenticationError",
        "SpnegoError",
        "BadMechanismError",
        "NotConnected",
        "ConnectionReset",
        "ConnectionDisconnected",
        "BrokenPipe",
        "LogonFailure",
        "STATUS_NETWORK_SESSION_EXPIRED",
        "STATUS_USER_SESSION_DELETED",
    )
    return any(marker in exc_type or marker in message for marker in retry_markers)


def run_with_session_retry(operation: str, action):
    try:
        return action()
    except Exception as exc:
        if not _is_retryable_session_error(exc):
            raise

        log.warning(
            "Retrying SMB operation %s after resetting cached SMB connections: %s",
            operation,
            exc,
        )
        _reset_connection_cache()
        _register_session()
        return action()


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
