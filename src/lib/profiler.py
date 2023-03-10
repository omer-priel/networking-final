# Profiler for chrome://tracing

import calendar
import os
import os.path
import threading
import time
import traceback
from io import TextIOWrapper
from typing import Callable

# config
PROFILE_PATH = "profiles/profile.json"

# globals
isFirstEvent: bool = True
staretdTs: int = 0
profileStream: TextIOWrapper | None = None  # type: ignore[assignment]


def use_profiler(entryPoint: Callable[[], None]) -> None:
    global profileStream, staretdTs

    # remove the last profile.json and create the parent directory if needed
    if os.path.isfile(PROFILE_PATH):
        os.remove(PROFILE_PATH)
    elif not os.path.isdir(os.path.dirname(PROFILE_PATH)):
        os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)

    # create the profile file
    profileStream = open(PROFILE_PATH, "w")
    profileStream.write('{"displayTimeUnit":"ms","otherData": {},"traceEvents":[')

    # call the program
    try:
        staretdTs = calendar.timegm(time.gmtime())
        entryPoint()
    except BaseException:
        traceback.print_exc()
    finally:
        # close the profile file
        profileStream.write("]}")
        profileStream.close()


def profiler_add_event(name: str) -> None:
    global isFirstEvent

    if not profileStream:
        return None

    if isFirstEvent:
        isFirstEvent = False
    else:
        profileStream.write(",")

    name = name.replace('"', "'")
    ts = calendar.timegm(time.gmtime()) - staretdTs
    tid = threading.current_thread().native_id
    profileStream.write(
        "{"
        + '"name": "{}", "cat": "Event", "ph": "X", "dur": 100, "ts": {}, "pid": 0, "tid": {} '.format(name, ts, tid)
        + "}"
    )


def profiler_add_scope(name: str, startTs: int, endTs: int) -> None:
    global isFirstEvent

    if not profileStream:
        return None

    startTs -= staretdTs
    endTs -= staretdTs

    if isFirstEvent:
        isFirstEvent = False
    else:
        profileStream.write(",")

    name = name.replace('"', "'")
    tid = threading.current_thread().native_id
    profileStream.write(
        "{"
        + '"name": "{}", "cat": "Scope", "ph": "X", "dur": {}, "ts": {}, "pid": 0, "tid": {} '.format(
            name, endTs - startTs, startTs, tid
        )
        + "}"
    )


class ProfilerScope:
    def __init__(self, scopeName: str) -> None:
        self.scopeName = scopeName
        self.startTs = calendar.timegm(time.gmtime())

    def close(self) -> None:
        endTs = calendar.timegm(time.gmtime())
        profiler_add_scope(self.scopeName, self.startTs, endTs)


def profiler_scope(scopeName: str | None = None):  # type: ignore [no-untyped-def]
    def decorator(function: Callable):  # type: ignore [no-untyped-def]
        def wrapper(*args, **kwargs):  # type: ignore [no-untyped-def]
            startTs = calendar.timegm(time.gmtime())

            error: BaseException | None = None
            try:
                ret = function(*args, **kwargs)
            except BaseException as ex:
                error = ex

            endTs = calendar.timegm(time.gmtime())

            if scopeName:
                profiler_add_scope(scopeName, startTs, endTs)
            else:
                profiler_add_scope(function.__name__, startTs, endTs)

            if error:
                raise error

            return ret

        return wrapper

    return decorator
