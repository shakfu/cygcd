#!/usr/bin/env python3
"""
signal_source.py - Demonstrates dispatch source for Unix signals.

SignalSource allows handling signals asynchronously on a dispatch queue
instead of using traditional signal handlers.
"""

import os
import signal
import time
import pygcd


def main():
    print("=== Signal Source Demo ===")
    print(f"PID: {os.getpid()}")
    print("Send SIGUSR1 to this process to trigger the handler")
    print("Example: kill -USR1", os.getpid())
    print()

    signal_count = [0]

    def on_signal():
        signal_count[0] += 1
        print(f"Received SIGUSR1! (count: {signal_count[0]})")

    # Disable default signal handling - required for dispatch sources
    old_handler = signal.signal(signal.SIGUSR1, signal.SIG_IGN)

    try:
        # Create a signal source on a serial queue
        q = pygcd.Queue("signal.handler")
        source = pygcd.SignalSource(signal.SIGUSR1, on_signal, queue=q)
        source.start()

        print("Signal handler active. Sending 3 test signals...")
        print()

        # Send signals to ourselves
        for i in range(3):
            time.sleep(0.5)
            os.kill(os.getpid(), signal.SIGUSR1)

        # Wait for handlers to complete
        time.sleep(0.2)

        print()
        print(f"Total signals received: {signal_count[0]}")

        # Clean up
        source.cancel()

    finally:
        # Restore original handler
        signal.signal(signal.SIGUSR1, old_handler)

    print("\n=== Multiple Signals Demo ===")

    counts = {"USR1": 0, "USR2": 0}

    def on_usr1():
        counts["USR1"] += 1
        print(f"SIGUSR1 received (total: {counts['USR1']})")

    def on_usr2():
        counts["USR2"] += 1
        print(f"SIGUSR2 received (total: {counts['USR2']})")

    # Set up handlers for both signals
    old_usr1 = signal.signal(signal.SIGUSR1, signal.SIG_IGN)
    old_usr2 = signal.signal(signal.SIGUSR2, signal.SIG_IGN)

    try:
        q = pygcd.Queue("multi.signal")
        src1 = pygcd.SignalSource(signal.SIGUSR1, on_usr1, queue=q)
        src2 = pygcd.SignalSource(signal.SIGUSR2, on_usr2, queue=q)

        src1.start()
        src2.start()

        # Send alternating signals
        for _ in range(2):
            os.kill(os.getpid(), signal.SIGUSR1)
            time.sleep(0.1)
            os.kill(os.getpid(), signal.SIGUSR2)
            time.sleep(0.1)

        time.sleep(0.2)

        src1.cancel()
        src2.cancel()

        print(f"\nFinal counts: USR1={counts['USR1']}, USR2={counts['USR2']}")

    finally:
        signal.signal(signal.SIGUSR1, old_usr1)
        signal.signal(signal.SIGUSR2, old_usr2)


if __name__ == "__main__":
    main()
