# StorageBackend interface (architecture.md §2). No file-touching code
# anywhere else in the app should call open() or a filesystem path directly —
# always go through get_storage_backend() in factory.py.
