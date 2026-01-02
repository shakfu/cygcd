"""
cygcd - Python wrapper for macOS Grand Central Dispatch (GCD).

Provides Python bindings to Apple's GCD framework for concurrent programming.

Example usage:
    >>> import cygcd
    >>> q = cygcd.Queue("my.queue")
    >>> results = []
    >>> q.run_sync(lambda: results.append(1))
    >>> results
    [1]
"""

from cygcd._core import (
    # Classes
    Queue,
    Group,
    Semaphore,
    Once,
    Timer,
    SignalSource,
    ReadSource,
    WriteSource,
    ProcessSource,
    Data,
    Workloop,
    IOChannel,
    # Functions
    apply,
    time_from_now,
    walltime,
    read_async,
    write_async,
    get_specific,
    # Time constants
    DISPATCH_TIME_NOW,
    DISPATCH_TIME_FOREVER,
    NSEC_PER_SEC_PY as NSEC_PER_SEC,
    NSEC_PER_MSEC_PY as NSEC_PER_MSEC,
    NSEC_PER_USEC_PY as NSEC_PER_USEC,
    USEC_PER_SEC_PY as USEC_PER_SEC,
    MSEC_PER_SEC_PY as MSEC_PER_SEC,
    # Queue priority constants
    QUEUE_PRIORITY_HIGH,
    QUEUE_PRIORITY_DEFAULT,
    QUEUE_PRIORITY_LOW,
    QUEUE_PRIORITY_BACKGROUND,
    # QOS class constants
    QOS_CLASS_USER_INTERACTIVE,
    QOS_CLASS_USER_INITIATED,
    QOS_CLASS_DEFAULT,
    QOS_CLASS_UTILITY,
    QOS_CLASS_BACKGROUND,
    QOS_CLASS_UNSPECIFIED,
    # Process event flags
    PROC_EXIT,
    PROC_FORK,
    PROC_EXEC,
    PROC_SIGNAL,
    # I/O type constants
    IO_STREAM,
    IO_RANDOM,
    IO_STOP,
    # Autorelease frequency constants
    AUTORELEASE_FREQUENCY_INHERIT,
    AUTORELEASE_FREQUENCY_WORK_ITEM,
    AUTORELEASE_FREQUENCY_NEVER,
)

__all__ = [
    # Classes
    "Queue",
    "Group",
    "Semaphore",
    "Once",
    "Timer",
    "SignalSource",
    "ReadSource",
    "WriteSource",
    "ProcessSource",
    "Data",
    "Workloop",
    "IOChannel",
    # Functions
    "apply",
    "time_from_now",
    "walltime",
    "read_async",
    "write_async",
    "get_specific",
    # Time constants
    "DISPATCH_TIME_NOW",
    "DISPATCH_TIME_FOREVER",
    "NSEC_PER_SEC",
    "NSEC_PER_MSEC",
    "NSEC_PER_USEC",
    "USEC_PER_SEC",
    "MSEC_PER_SEC",
    # Queue priority constants
    "QUEUE_PRIORITY_HIGH",
    "QUEUE_PRIORITY_DEFAULT",
    "QUEUE_PRIORITY_LOW",
    "QUEUE_PRIORITY_BACKGROUND",
    # QOS class constants
    "QOS_CLASS_USER_INTERACTIVE",
    "QOS_CLASS_USER_INITIATED",
    "QOS_CLASS_DEFAULT",
    "QOS_CLASS_UTILITY",
    "QOS_CLASS_BACKGROUND",
    "QOS_CLASS_UNSPECIFIED",
    # Process event flags
    "PROC_EXIT",
    "PROC_FORK",
    "PROC_EXEC",
    "PROC_SIGNAL",
    # I/O type constants
    "IO_STREAM",
    "IO_RANDOM",
    "IO_STOP",
    # Autorelease frequency constants
    "AUTORELEASE_FREQUENCY_INHERIT",
    "AUTORELEASE_FREQUENCY_WORK_ITEM",
    "AUTORELEASE_FREQUENCY_NEVER",
]
__version__ = "0.2.0"
