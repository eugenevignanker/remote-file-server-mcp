import json

import smbclient

from smb.helpers import smb_path
from smb.session import run_with_session_retry
from utils.logger import audit
from utils.validators import safe_relative_path, sanitised_error


def register(mcp) -> None:
    @mcp.tool()
    def make_directory(path: str, exist_ok: bool = True) -> str:
        """
        Create a directory within the exposed SMB root.

        Args:
            path: Relative directory path to create.
            exist_ok: Whether an existing directory is acceptable (default: true).

        Returns:
            JSON object describing the created directory.
        """
        try:
            relative = safe_relative_path(path)
            if not relative:
                audit("make_directory", path, "denied", reason="empty path")
                return json.dumps({"error": "A directory path is required."})
        except ValueError as exc:
            audit("make_directory", path, "denied", reason=str(exc))
            return json.dumps({"error": str(exc)})

        smb_dir = smb_path(relative)
        try:
            def _mkdir() -> str:
                smbclient.makedirs(smb_dir, exist_ok=exist_ok)
                audit("make_directory", relative, "success", exist_ok=exist_ok)
                return json.dumps({
                    "path": relative,
                    "created": True,
                }, indent=2)

            return run_with_session_retry("make_directory", _mkdir)
        except Exception as exc:
            audit("make_directory", relative, "error")
            return sanitised_error(exc)
