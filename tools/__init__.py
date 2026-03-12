from . import get_file_info, list_files, read_file, search_files


def register_all(mcp) -> None:
    list_files.register(mcp)
    read_file.register(mcp)
    get_file_info.register(mcp)
    search_files.register(mcp)
