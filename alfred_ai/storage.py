"""Owner-protected retained uploads using Django's existing file storage."""
import os
from pathlib import Path

from django.core.files.storage import FileSystemStorage
from alfred_private_storage import private_directory, PrivateStorageUnavailable


class PrivateFileSystemStorage(FileSystemStorage):
    def _save(self, name, content):
        if os.name == "nt":
            try:
                private_directory(Path(self.location))
            except (OSError, ValueError, PrivateStorageUnavailable):
                raise PermissionError("Private media storage requires authorized permission repair.") from None
        return super()._save(name, content)
