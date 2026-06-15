#!/usr/bin/env python3
"""
log_no_question.py — Record calls where the caller declined to ask a question.

Called by the dialplan as:
  AGI(log_no_question.py,${CALLID},${LANGUAGE},<status>)

status values:
  no_question  — caller pressed 2 (no) at the question prompt
  timeout      — caller did not press anything at the question prompt
  lang_timeout — caller did not press anything at the language menu

Writes one row to `calls`, one row to `asterisk_cdr`, and one row to
`system_log` so every answered call has a complete DB record.
"""

import sys
from datetime import datetime

from agi_lib import agi_io, db


def main() -> None:
    agi_env = agi_io.read_env()
    start_time = datetime.now()

    call_id   = sys.argv[1] if len(sys.argv) > 1 else agi_env.get("agi_uniqueid", "unknown")
    language  = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
    status    = sys.argv[3] if len(sys.argv) > 3 else "no_question"

    caller_id = agi_env.get("agi_callerid", "unknown")
    extension = agi_env.get("agi_dnid", agi_env.get("agi_extension", "unknown"))

    agi_io.verbose(f"log_no_question: caller={caller_id} call={call_id} lang={language} status={status}")

    db.insert_no_question_call(call_id, caller_id, extension, language, status)
    db.insert_cdr(call_id, caller_id, extension, start_time, datetime.now())
    db.log_event(
        "INFO",
        "call_no_question",
        f"Caller {caller_id} did not ask questions (status={status})",
        call_id=call_id,
    )

    agi_io.send("200 result=1")


if __name__ == "__main__":
    main()
