#!/usr/bin/env python3
"""
fd_source.py - Demonstrates dispatch sources for file descriptor I/O.

ReadSource monitors a file descriptor for available data.
WriteSource monitors a file descriptor for write availability.

These are useful for building event-driven I/O without blocking.
"""

import os
import time
import pygcd


def main():
    print("=== ReadSource Demo ===")
    print("Using a pipe to demonstrate read monitoring\n")

    # Create a pipe
    read_fd, write_fd = os.pipe()

    messages_received = []

    def on_readable():
        # Read available data
        data = os.read(read_fd, 1024)
        if data:
            msg = data.decode('utf-8')
            messages_received.append(msg)
            print(f"Received: {msg!r}")

    # Create read source
    q = pygcd.Queue("io.queue")
    reader = pygcd.ReadSource(read_fd, on_readable, queue=q)
    reader.start()

    # Write some messages
    print("Writing messages to pipe...")
    for i in range(3):
        msg = f"Message {i + 1}"
        os.write(write_fd, msg.encode('utf-8'))
        print(f"Sent: {msg!r}")
        time.sleep(0.1)

    time.sleep(0.2)
    reader.cancel()

    print(f"\nTotal messages received: {len(messages_received)}")

    # Clean up
    os.close(read_fd)
    os.close(write_fd)

    print("\n=== WriteSource Demo ===")
    print("Monitoring pipe for write availability\n")

    # Create new pipe
    read_fd, write_fd = os.pipe()

    write_count = [0]

    def on_writable():
        write_count[0] += 1
        if write_count[0] <= 3:
            msg = f"Auto-write {write_count[0]}"
            os.write(write_fd, msg.encode('utf-8'))
            print(f"Write handler fired, wrote: {msg!r}")

    # Create write source
    writer = pygcd.WriteSource(write_fd, on_writable, queue=q)
    writer.start()

    # Let write source fire a few times
    time.sleep(0.3)
    writer.cancel()

    # Read what was written
    print("\nReading back written data:")
    while True:
        try:
            os.set_blocking(read_fd, False)
            data = os.read(read_fd, 1024)
            if data:
                print(f"  Read: {data.decode('utf-8')!r}")
            else:
                break
        except BlockingIOError:
            break

    os.close(read_fd)
    os.close(write_fd)

    print("\n=== Producer-Consumer with Dispatch Sources ===")

    # Create pipe for communication
    read_fd, write_fd = os.pipe()

    received = []
    done = [False]

    def consumer():
        data = os.read(read_fd, 1024)
        if data:
            msg = data.decode('utf-8')
            received.append(msg)
            print(f"Consumer received: {msg}")
            if msg == "END":
                done[0] = True

    consumer_queue = pygcd.Queue("consumer")
    read_source = pygcd.ReadSource(read_fd, consumer, queue=consumer_queue)
    read_source.start()

    # Producer sends messages
    producer_queue = pygcd.Queue("producer")
    messages = ["Hello", "World", "From", "GCD", "END"]

    def send_next(idx):
        if idx < len(messages):
            msg = messages[idx]
            os.write(write_fd, msg.encode('utf-8'))
            print(f"Producer sent: {msg}")
            # Schedule next send
            producer_queue.after(0.1, lambda: send_next(idx + 1))

    send_next(0)

    # Wait for completion
    while not done[0]:
        time.sleep(0.1)

    time.sleep(0.1)
    read_source.cancel()

    print(f"\nAll messages transferred: {received}")

    os.close(read_fd)
    os.close(write_fd)


if __name__ == "__main__":
    main()
