# StorageBackend interface + LocalFileSystemBackend / S3Backend land here in
# Phase 4 (architecture.md §2). No file-touching code anywhere else in the app
# should call open() or a filesystem path directly — always go through this module.
