import os

from .parser import SourceLocation


class Error(Exception):
    def __init__(self, source_location: SourceLocation, description: str) -> None:
        short_file_name = os.path.basename(source_location.file_name)
        super().__init__(
            f"{short_file_name}:{source_location.line_number}:{source_location.column_number}: {description}"
        )
