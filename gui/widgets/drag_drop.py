from pathlib import Path


def dropped_file_path(mime_data, extensions):
    """Returns the local path of the first dropped file whose extension is
    in `extensions`, or None if the drag doesn't carry a matching one.
    Used both to decide whether to accept a drag as it enters a widget and
    to pull the actual path out once it's dropped."""
    if not mime_data.hasUrls():
        return None

    allowed = {ext.lower() for ext in extensions}
    for url in mime_data.urls():
        if url.isLocalFile():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in allowed:
                return path
    return None

