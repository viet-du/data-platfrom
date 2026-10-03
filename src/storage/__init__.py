"""Public API cho storage layer.

Eager: nothing (avoid import-time side effects).
Lazy: mọi class/function qua PEP 562 __getattr__ — để:
  1. Tránh ImportError khi google-api-python-client / google-auth chưa sẵn sàng.
  2. Bot vẫn boot được khi thiếu credentials.
  3. Tránh partial-init khi các module phụ thuộc lẫn nhau.

Public API:
  CloudSink:           abstract base
  GoogleDriveSink:     Drive-backed implementation
  LocalJsonSink:       local fallback
  build_sink_from_env: factory chọn sink theo env vars
  DrivePuller:         pull từ Drive về local
  get_drive_puller:    singleton factory
"""
_LAZY_EXPORTS = {
    "CloudSink": ("cloud_sink", "CloudSink"),
    "GoogleDriveSink": ("cloud_sink", "GoogleDriveSink"),
    "LocalJsonSink": ("cloud_sink", "LocalJsonSink"),
    "build_sink_from_env": ("cloud_sink", "build_sink_from_env"),
    "DrivePuller": ("drive_puller", "DrivePuller"),
    "get_drive_puller": ("drive_puller", "get_drive_puller"),
    "UploadRetryQueue": ("retry_queue", "UploadRetryQueue"),
    "get_retry_queue": ("retry_queue", "get_retry_queue"),
}


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        mod_name, attr_name = _LAZY_EXPORTS[name]
        from importlib import import_module
        module = import_module(f"{__name__}.{mod_name}")
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CloudSink",
    "GoogleDriveSink",
    "LocalJsonSink",
    "build_sink_from_env",
    "DrivePuller",
    "get_drive_puller",
    "UploadRetryQueue",
    "get_retry_queue",
]