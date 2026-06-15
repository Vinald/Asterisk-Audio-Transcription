"""AGI I/O primitives — send/receive lines and read the AGI environment header block."""

import sys


def send(msg: str) -> None:
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def recv() -> str:
    return sys.stdin.readline().strip()


def set_variable(name: str, value: str) -> None:
    send(f"SET VARIABLE {name} {value}")
    recv()


def verbose(msg: str) -> None:
    safe = msg.replace('"', "'")
    send(f'VERBOSE "{safe}" 1')
    recv()


def read_env() -> dict:
    """Consume the AGI environment header block sent by Asterisk on stdin."""
    env = {}
    while True:
        line = sys.stdin.readline().strip()
        if not line:
            break
        if ":" in line:
            key, _, value = line.partition(":")
            env[key.strip()] = value.strip()
    return env
