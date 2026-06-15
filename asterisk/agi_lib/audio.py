"""Audio download and format conversion for Asterisk playback."""

import os
import subprocess

import requests

from . import agi_io


def download(url: str, dest_path: str) -> None:
    """Download audio from URL to dest_path."""
    agi_io.verbose("Downloading response audio...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        f.write(resp.content)


def convert_to_asterisk_format(src_path: str, dest_path: str) -> None:
    """Convert any WAV to 8 kHz mono 16-bit signed-integer PCM (Asterisk native)."""
    agi_io.verbose("Converting to 8 kHz mono for Asterisk...")
    subprocess.run(
        ["sox", src_path, "-r", "8000", "-c", "1", "-b", "16", "-e", "signed-integer", dest_path],
        check=True,
        stderr=subprocess.DEVNULL,
    )


def set_world_readable(path: str) -> None:
    """Make a file world-readable so the asterisk user can play it back."""
    old_umask = os.umask(0o000)
    try:
        os.chmod(path, 0o777)
    finally:
        os.umask(old_umask)


def download_and_prepare(url: str, output_path: str) -> str:
    """Download audio URL, convert to Asterisk format, and chmod 777."""
    tmp_path = output_path + "_tmp.wav"
    download(url, tmp_path)
    convert_to_asterisk_format(tmp_path, output_path)
    os.remove(tmp_path)
    set_world_readable(output_path)
    agi_io.verbose(f"Audio ready: {output_path}")
    return output_path
