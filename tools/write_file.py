import json
import posixpath

import smbclient

from smb.helpers import smb_path
from smb.session import run_with_session_retry
from utils.logger import audit
from utils.validators import check_filename_denylist, safe_relative_path, sanitised_error


def register(mcp) -> None:
    @mcp.tool()
    def write_file(path: str, content: str, overwrite: bool = True) -> str:
        """
        Write text content to a file on the SMB share.

        Args:
            path: Relative destination path within the exposed root.
            content: Full text content to write.
            overwrite: Whether to replace an existing file (default: true).

        Returns:
            JSON object describing the written file.
        """
        try:
            relative = safe_relative_path(path)
            if not relative:
                audit("write_file", path, "denied", reason="empty path")
                return json.dumps({"error": "A file path is required."})
            filename = posixpath.basename(relative)
            check_filename_denylist(filename)
        except ValueError as exc:
            audit("write_file", path, "denied", reason=str(exc))
            return json.dumps({"error": str(exc)})

        smb_file = smb_path(relative)
        parent = posixpath.dirname(relative)
        smb_parent = smb_path(parent) if parent else None

        try:
            def _write() -> str:
                if smb_parent:
                    smbclient.makedirs(smb_parent, exist_ok=True)

                if not overwrite and smbclient.path.exists(smb_file):
                    audit("write_file", relative, "denied", reason="exists")
                    return json.dumps({"error": "Destination already exists."})

                with smbclient.open_file(smb_file, mode="w", encoding="utf-8") as f:
                    f.write(content)

                size_bytes = len(content.encode("utf-8"))
                audit("write_file", relative, "success", file_size_bytes=size_bytes, overwrite=overwrite)
                return json.dumps({
                    "path": relative,
                    "bytes_written": size_bytes,
                    "overwritten": overwrite,
                }, indent=2)

            return run_with_session_retry("write_file", _write)
        except Exception as exc:
            audit("write_file", relative, "error")
            return sanitised_error(exc)
