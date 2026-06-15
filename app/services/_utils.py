import contextlib
import os
import time


@contextlib.contextmanager
def temp_audio(prefix: str):
    """Yield a unique /tmp path for an audio file, then delete it on exit."""
    path = f"/tmp/{prefix}_{os.getpid()}_{int(time.time())}.wav"
    try:
        yield path
    finally:
        if os.path.exists(path):
            os.remove(path)
