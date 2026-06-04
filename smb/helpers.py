import fnmatch

import smbclient

from config import SMB_HOST, SMB_SHARE, SMB_SUBFOLDER
from utils.validators import check_filename_denylist

SHARE_ROOT_UNC = f"\\\\{SMB_HOST}\\{SMB_SHARE}"
if SMB_SUBFOLDER:
    SHARE_ROOT_UNC = f"{SHARE_ROOT_UNC}\\{SMB_SUBFOLDER.replace('/', chr(92))}"
SEARCH_MAX_RESULTS = 200


def smb_path(relative: str) -> str:
    """Build a UNC path from an already-validated relative path."""
    base = SHARE_ROOT_UNC
    if relative:
        return f"{base}\\{relative.replace('/', chr(92))}"
    return base


def unc_to_relative(full_unc: str) -> str:
    """Strip the share root UNC prefix and return a forward-slash relative path."""
    return full_unc[len(SHARE_ROOT_UNC):].lstrip("\\").replace("\\", "/")


def file_size_safe(full_unc: str) -> int | None:
    """Return the file size in bytes, or None if the stat call fails."""
    try:
        return smbclient.stat(full_unc).st_size
    except Exception:
        return None


def collect_matches(
    dirpath: str,
    filenames: list[str],
    pattern: str,
) -> list[dict[str, object]]:
    """
    Filter filenames in a single directory by pattern and denylist.
    Returns a list of result dicts ready to append to the search results.
    """
    matches = []
    for filename in filenames:
        if not fnmatch.fnmatch(filename.lower(), pattern.lower()):
            continue
        try:
            check_filename_denylist(filename)
        except ValueError:
            continue  # silently skip denied files
        full_unc = f"{dirpath}\\{filename}"
        matches.append({
            "path": unc_to_relative(full_unc),
            "name": filename,
            "size_bytes": file_size_safe(full_unc),
        })
    return matches
