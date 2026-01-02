#!/usr/bin/env python3
"""
process_source.py - Demonstrates dispatch source for process events.

ProcessSource monitors a process for lifecycle events:
- PROC_EXIT: Process has exited
- PROC_FORK: Process has forked
- PROC_EXEC: Process has exec'd a new image
- PROC_SIGNAL: Process has received a signal
"""

import os
import subprocess
import time
import pygcd


def main():
    print("=== Process Exit Monitoring ===")
    print("Launching child processes and monitoring for exit...\n")

    exits = []

    def make_exit_handler(name):
        def handler():
            exits.append(name)
            print(f"Process '{name}' has exited!")
        return handler

    # Launch several child processes with different durations
    processes = []
    sources = []
    q = pygcd.Queue("process.monitor")

    for i, delay in enumerate([0.3, 0.1, 0.2]):
        name = f"child_{i + 1}"
        proc = subprocess.Popen(["sleep", str(delay)])
        processes.append((name, proc))

        # Monitor for exit
        source = pygcd.ProcessSource(
            proc.pid,
            make_exit_handler(name),
            events=pygcd.PROC_EXIT,
            queue=q
        )
        source.start()
        sources.append(source)
        print(f"Launched {name} (PID {proc.pid}), will run for {delay}s")

    print("\nWaiting for processes to exit...")

    # Wait for all to complete
    for name, proc in processes:
        proc.wait()

    time.sleep(0.2)

    # Cancel all sources
    for source in sources:
        source.cancel()

    print(f"\nExit order: {exits}")

    print("\n=== Process Exit with Timeout ===")

    exited = [False]

    def on_exit():
        exited[0] = True
        print("Long-running process exited!")

    # Launch a process that takes a while
    proc = subprocess.Popen(["sleep", "2"])
    print(f"Launched long-running process (PID {proc.pid})")

    source = pygcd.ProcessSource(proc.pid, on_exit, events=pygcd.PROC_EXIT, queue=q)
    source.start()

    # Wait a bit, then terminate
    print("Waiting 0.5s then terminating...")
    time.sleep(0.5)

    if not exited[0]:
        print("Sending SIGTERM to process")
        proc.terminate()

    proc.wait()
    time.sleep(0.1)

    source.cancel()
    print(f"Process terminated, exited flag: {exited[0]}")

    print("\n=== Monitoring Multiple Events ===")

    events_seen = []

    def on_events():
        events_seen.append(time.time())
        print(f"Event detected! (total: {len(events_seen)})")

    # Launch a process that forks
    # Using Python to demonstrate fork detection
    script = """
import os
import time
pid = os.fork()
if pid == 0:
    # Child
    time.sleep(0.1)
    os._exit(0)
else:
    # Parent waits for child
    os.waitpid(pid, 0)
    time.sleep(0.2)
"""

    proc = subprocess.Popen(["python3", "-c", script])
    print(f"Launched forking process (PID {proc.pid})")

    # Monitor for fork and exit events
    source = pygcd.ProcessSource(
        proc.pid,
        on_events,
        events=pygcd.PROC_FORK | pygcd.PROC_EXIT,
        queue=q
    )
    source.start()

    proc.wait()
    time.sleep(0.3)

    source.cancel()
    print(f"\nTotal events detected: {len(events_seen)}")

    print("\n=== Simple Process Watcher ===")

    def watch_process(cmd, timeout=5.0):
        """Run a command and monitor for its exit."""
        completed = [False]
        exit_time = [None]
        start_time = time.time()

        def on_done():
            completed[0] = True
            exit_time[0] = time.time() - start_time

        proc = subprocess.Popen(cmd, shell=True)
        source = pygcd.ProcessSource(proc.pid, on_done, queue=q)
        source.start()

        print(f"Running: {cmd}")

        # Wait with timeout
        deadline = time.time() + timeout
        while not completed[0] and time.time() < deadline:
            time.sleep(0.05)

        if completed[0]:
            print(f"Completed in {exit_time[0]:.3f}s")
        else:
            print("Timeout! Killing process...")
            proc.kill()
            proc.wait()

        source.cancel()
        return completed[0]

    watch_process("echo 'Hello from subprocess!' && sleep 0.2")
    print()
    watch_process("sleep 0.3")


if __name__ == "__main__":
    main()
