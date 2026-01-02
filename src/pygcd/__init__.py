"""
pygcd - Python wrapper for macOS Grand Central Dispatch (GCD).

Provides Python bindings to Apple's GCD framework for concurrent programming.

Example usage:
    >>> import pygcd
    >>> q = pygcd.Queue("my.queue")
    >>> results = []
    >>> q.run_sync(lambda: results.append(1))
    >>> results
    [1]
"""

from pygcd._core import (
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
    # Functions
    apply,
    time_from_now,
    walltime,
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
    # Functions
    "apply",
    "time_from_now",
    "walltime",
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
]
__version__ = "0.2.0"
