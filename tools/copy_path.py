import json
import posixpath

import smbclient

from smb.helpers import smb_path
from smb.session import run_with_session_retry
from utils.logger import audit
from utils.validators import check_filename_denylist, safe_relative_path, sanitised_error


def _copy_file(source_unc: str, destination_unc: str) -> int:
    total_bytes = 0
    with smbclient.open_file(source_unc, mode="rb") as src:
        with smbclient.open_file(destination_unc, mode="wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
                total_bytes += len(chunk)
    return total_bytes


def _copy_directory(source_unc: str, destination_unc: str, overwrite: bool) -> int:
    smbclient.makedirs(destination_unc, exist_ok=True)
    copied_files = 0

    for dirpath, dirnames, filenames in smbclient.walk(source_unc):
        relative_dir = dirpath[len(source_unc):].lstrip("\\").replace("\\", "/")
        destination_dir = destination_unc
        if relative_dir:
            destination_dir = f"{destination_unc}\\{relative_dir.replace('/', chr(92))}"
            smbclient.makedirs(destination_dir, exist_ok=True)

        for dirname in dirnames:
            smbclient.makedirs(f"{destination_dir}\\{dirname}", exist_ok=True)

        for filename in filenames:
            check_filename_denylist(filename)
            source_file = f"{dirpath}\\{filename}"
            destination_file = f"{destination_dir}\\{filename}"
            if not overwrite and smbclient.path.exists(destination_file):
                raise FileExistsError(destination_file)
            _copy_file(source_file, destination_file)
            copied_files += 1

    return copied_files


def register(mcp) -> None:
    @mcp.tool()
    def copy_path(source_path: str, destination_path: str, overwrite: bool = False) -> str:
        """
        Copy a file or directory within the exposed SMB root.

        Args:
            source_path: Existing relative source path.
            destination_path: Relative destination path.
            overwrite: Whether existing destination files may be replaced.

        Returns:
            JSON object describing the copy operation.
        """
        try:
            source_relative = safe_relative_path(source_path)
            destination_relative = safe_relative_path(destination_path)
            if not source_relative or not destination_relative:
                audit("copy_path", source_path, "denied", destination=destination_path, reason="empty path")
                return json.dumps({"error": "Both source_path and destination_path are required."})
            check_filename_denylist(posixpath.basename(source_relative))
            check_filename_denylist(posixpath.basename(destination_relative))
        except ValueError as exc:
            audit("copy_path", source_path, "denied", destination=destination_path, reason=str(exc))
            return json.dumps({"error": str(exc)})

        source_unc = smb_path(source_relative)
        destination_unc = smb_path(destination_relative)
        destination_parent = posixpath.dirname(destination_relative)

        try:
            def _copy() -> str:
                if destination_parent:
                    smbclient.makedirs(smb_path(destination_parent), exist_ok=True)

                if smbclient.path.isdir(source_unc):
                    copied_files = _copy_directory(source_unc, destination_unc, overwrite)
                    result = {
                        "source_path": source_relative,
                        "destination_path": destination_relative,
                        "copied_type": "directory",
                        "files_copied": copied_files,
                    }
                else:
                    if not overwrite and smbclient.path.exists(destination_unc):
                        audit("copy_path", source_relative, "denied", destination=destination_relative, reason="exists")
                        return json.dumps({"error": "Destination already exists."})
                    bytes_copied = _copy_file(source_unc, destination_unc)
                    result = {
                        "source_path": source_relative,
                        "destination_path": destination_relative,
                        "copied_type": "file",
                        "bytes_copied": bytes_copied,
                    }

                audit("copy_path", source_relative, "success", destination=destination_relative, overwrite=overwrite)
                return json.dumps(result, indent=2)

            return run_with_session_retry("copy_path", _copy)
        except FileExistsError:
            audit("copy_path", source_relative, "denied", destination=destination_relative, reason="exists")
            return json.dumps({"error": "Destination already exists."})
        except Exception as exc:
            audit("copy_path", source_relative, "error", destination=destination_relative, overwrite=overwrite)
            return sanitised_error(exc)
