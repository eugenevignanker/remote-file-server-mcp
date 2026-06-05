import json
import posixpath

import smbclient

from smb.helpers import smb_path
from utils.logger import audit
from utils.validators import check_filename_denylist, safe_relative_path, sanitised_error


def _delete_directory_recursive(smb_dir: str) -> None:
    for dirpath, dirnames, filenames in smbclient.walk(smb_dir, topdown=False):
        for filename in filenames:
            smbclient.remove(f"{dirpath}\\{filename}")
        for dirname in dirnames:
            smbclient.rmdir(f"{dirpath}\\{dirname}")
    smbclient.rmdir(smb_dir)


def register(mcp) -> None:
    @mcp.tool()
    def delete_path(path: str, recursive: bool = False) -> str:
        """
        Delete a file or directory from the exposed SMB root.

        Args:
            path: Relative path to delete.
            recursive: Required for deleting non-empty directories.

        Returns:
            JSON object describing the deleted path.
        """
        try:
            relative = safe_relative_path(path)
            if not relative:
                audit("delete_path", path, "denied", reason="empty path")
                return json.dumps({"error": "A path is required."})
            name = posixpath.basename(relative)
            check_filename_denylist(name)
        except ValueError as exc:
            audit("delete_path", path, "denied", reason=str(exc))
            return json.dumps({"error": str(exc)})

        smb_target = smb_path(relative)
        try:
            if smbclient.path.isdir(smb_target):
                if recursive:
                    _delete_directory_recursive(smb_target)
                else:
                    smbclient.rmdir(smb_target)
            else:
                smbclient.remove(smb_target)

            audit("delete_path", relative, "success", recursive=recursive)
            return json.dumps({
                "path": relative,
                "deleted": True,
            }, indent=2)
        except Exception as exc:
            audit("delete_path", relative, "error", recursive=recursive)
            return sanitised_error(exc)
