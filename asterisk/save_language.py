#!/usr/bin/env python3
"""
save_language.py — Persist the caller's language selection to MySQL.

Called by Asterisk dialplan as:
  AGI(save_language.py,${CALLID},<lang_code>)

Writes:
  caller_preferences — remembers the language for future calls
  calls              — sets the language column on the active call row
"""

import sys

from agi_lib import agi_io, db


def save(uniqueid: str, caller_id: str, language: str) -> bool:
    pref_ok = db.upsert_language_preference(caller_id, language)
    lang_ok = db.update_call_language(uniqueid, language)
    return pref_ok and lang_ok


def main() -> None:
    agi_env = agi_io.read_env()

    if len(sys.argv) < 3:
        agi_io.verbose("save_language.py: missing arguments (expected UNIQUEID LANG)")
        agi_io.send("200 result=0")
        return

    uniqueid  = sys.argv[1]
    language  = sys.argv[2]
    caller_id = agi_env.get("agi_callerid", "unknown")

    agi_io.verbose(f"save_language: caller={caller_id} call={uniqueid} lang={language}")

    if save(uniqueid, caller_id, language):
        agi_io.verbose("save_language: saved OK")
        agi_io.send("200 result=1")
    else:
        agi_io.verbose("save_language: DB write failed")
        agi_io.send("200 result=0")


if __name__ == "__main__":
    main()
