import datetime
import json
import stat as statmod
import posixpath

import smbclient

from smb.helpers import smb_path
from smb.session import run_with_session_retry
from utils.logger import audit
from utils.validators import check_filename_denylist, safe_relative_path, sanitised_error


def register(mcp) -> None:
    @mcp.tool()
    def get_file_info(path: str) -> str:
        """
        Return metadata for a file or directory on the SMB share without reading its contents.

        Args:
            path: Relative path to the file or directory within the share.
                  Forward or back slashes are both accepted.
                  Parent directory traversal (..) is not permitted.

        Returns:
            JSON object with keys: name, type ("file"|"directory"), size_bytes,
            modified_time (UTC ISO 8601), created_time (UTC ISO 8601).
        """
        try:
            relative = safe_relative_path(path)
            if not relative:
                return json.dumps({"error": "A path is required."})
            filename = posixpath.basename(relative)
            check_filename_denylist(filename)
        except ValueError as exc:
            audit("get_file_info", path, "denied", reason=str(exc))
            return json.dumps({"error": str(exc)})

        smb_target = smb_path(relative)
        try:
            def _stat() -> str:
                st = smbclient.stat(smb_target)
                is_dir = smbclient.path.isdir(smb_target)
                info = {
                    "name": posixpath.basename(relative),
                    "type": "directory" if is_dir else "file",
                    "size_bytes": st.st_size,
                    "modified_time": datetime.datetime.fromtimestamp(
                        st.st_mtime, tz=datetime.timezone.utc
                    ).isoformat(),
                    "created_time": datetime.datetime.fromtimestamp(
                        st.st_ctime, tz=datetime.timezone.utc
                    ).isoformat(),
                    "permissions": {
                        "mode": oct(st.st_mode),
                        "owner_read": bool(st.st_mode & statmod.S_IRUSR),
                        "owner_write": bool(st.st_mode & statmod.S_IWUSR),
                        "owner_execute": bool(st.st_mode & statmod.S_IXUSR),
                        "group_read": bool(st.st_mode & statmod.S_IRGRP),
                        "group_write": bool(st.st_mode & statmod.S_IWGRP),
                        "group_execute": bool(st.st_mode & statmod.S_IXGRP),
                        "other_read": bool(st.st_mode & statmod.S_IROTH),
                        "other_write": bool(st.st_mode & statmod.S_IWOTH),
                        "other_execute": bool(st.st_mode & statmod.S_IXOTH),
                    },
                }
                audit("get_file_info", relative, "success", file_size_bytes=st.st_size)
                return json.dumps(info, indent=2)

            return run_with_session_retry("get_file_info", _stat)
        except ValueError as exc:
            audit("get_file_info", relative, "denied", reason=str(exc))
            return json.dumps({"error": str(exc)})
        except Exception as exc:
            audit("get_file_info", relative, "error")
            return sanitised_error(exc)
