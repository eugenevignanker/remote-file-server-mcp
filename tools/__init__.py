from . import (
    copy_path,
    delete_path,
    get_file_info,
    list_files,
    make_directory,
    read_file,
    rename_path,
    search_files,
    write_file,
)


def register_all(mcp) -> None:
    list_files.register(mcp)
    read_file.register(mcp)
    get_file_info.register(mcp)
    search_files.register(mcp)
    write_file.register(mcp)
    delete_path.register(mcp)
    rename_path.register(mcp)
    copy_path.register(mcp)
    make_directory.register(mcp)
