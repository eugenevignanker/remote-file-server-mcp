import json
import posixpath

import smbclient

from smb.helpers import smb_path
from utils.logger import audit
from utils.validators import check_filename_denylist, safe_relative_path, sanitised_error


def register(mcp) -> None:
    @mcp.tool()
    def rename_path(source_path: str, destination_path: str, overwrite: bool = False) -> str:
        """
        Rename or move a file or directory within the exposed SMB root.

        Args:
            source_path: Existing relative path.
            destination_path: New relative path.
            overwrite: Whether to replace an existing destination.

        Returns:
            JSON object describing the rename.
        """
        try:
            source_relative = safe_relative_path(source_path)
            destination_relative = safe_relative_path(destination_path)
            if not source_relative or not destination_relative:
                audit("rename_path", source_path, "denied", destination=destination_path, reason="empty path")
                return json.dumps({"error": "Both source_path and destination_path are required."})
            check_filename_denylist(posixpath.basename(source_relative))
            check_filename_denylist(posixpath.basename(destination_relative))
        except ValueError as exc:
            audit("rename_path", source_path, "denied", destination=destination_path, reason=str(exc))
            return json.dumps({"error": str(exc)})

        source_unc = smb_path(source_relative)
        destination_unc = smb_path(destination_relative)
        destination_parent = posixpath.dirname(destination_relative)

        try:
            if destination_parent:
                smbclient.makedirs(smb_path(destination_parent), exist_ok=True)

            if overwrite:
                smbclient.replace(source_unc, destination_unc)
            else:
                if smbclient.path.exists(destination_unc):
                    audit("rename_path", source_relative, "denied", destination=destination_relative, reason="exists")
                    return json.dumps({"error": "Destination already exists."})
                smbclient.rename(source_unc, destination_unc)

            audit("rename_path", source_relative, "success", destination=destination_relative, overwrite=overwrite)
            return json.dumps({
                "source_path": source_relative,
                "destination_path": destination_relative,
                "overwritten": overwrite,
            }, indent=2)
        except Exception as exc:
            audit("rename_path", source_relative, "error", destination=destination_relative, overwrite=overwrite)
            return sanitised_error(exc)
