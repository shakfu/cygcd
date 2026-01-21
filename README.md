# cygcd

Python wrapper for Apple's Grand Central Dispatch (GCD) framework on macOS.

GCD provides a powerful API for concurrent programming, allowing you to execute tasks asynchronously on system-managed thread pools. This wrapper exposes the core GCD primitives to Python with proper GIL handling for true parallelism.

## Installation

```sh
pip install cygcd

# or

uv add gcd
```

To build

```bash
git clone https://github.com/shakfu/cygcd.git
cd cygcd
make
```

Requires macOS and Python 3.9+.

## Quick Start

```python
import cygcd

# Create a serial queue
q = cygcd.Queue("com.example.myqueue")

# Execute tasks asynchronously
q.run_async(lambda: print("Hello from GCD!"))

# Execute synchronously (blocks until complete)
q.run_sync(lambda: print("This runs and waits"))
```

## When to Use What

This library provides multiple primitives for different concurrency patterns. Here's a guide to choosing the right tool:

### Feature Comparison

| Feature | Purpose | Use When |
|---------|---------|----------|
| **Queue** | Task scheduling | You need to run code on background threads or serialize access to a resource |
| **Group** | Track multiple tasks | You need to wait for several async operations to complete |
| **Semaphore** | Resource limiting | You need to limit concurrent access (connection pools, rate limiting) |
| **Timer** | Periodic execution | You need recurring tasks or delayed one-shot execution |
| **IOChannel** | High-performance file I/O | You're reading/writing large files and need chunked, async I/O |
| **read_async/write_async** | Simple async I/O | You need basic async file operations without chunking |
| **ReadSource/WriteSource** | FD monitoring | You need to know when a file descriptor is readable/writable |
| **SignalSource** | Signal handling | You need to handle Unix signals asynchronously |
| **ProcessSource** | Process monitoring | You need to track child process lifecycle events |
| **Workloop** | Priority-sensitive work | You have mixed-priority tasks sharing resources (rare, mostly real-time/UI) |

### Common Patterns

**Pattern: Parallel Processing**
```python
# Use apply() for parallel for-loops
cygcd.apply(100, lambda i: process_item(i))

# Or use Group for heterogeneous tasks
g = cygcd.Group()
q = cygcd.Queue.global_queue()
g.run_async(q, task_a)
g.run_async(q, task_b)
g.wait()
```

**Pattern: Rate Limiting**
```python
# Semaphore limits concurrent operations
sem = cygcd.Semaphore(3)  # Max 3 concurrent

def limited_operation():
    sem.wait()
    try:
        do_work()
    finally:
        sem.signal()
```

**Pattern: Reader-Writer Lock**
```python
# Concurrent queue + barriers for reader-writer access
q = cygcd.Queue("rw", concurrent=True)
q.run_async(read_data)      # Readers run concurrently
q.run_async(read_data)
q.barrier_async(write_data) # Writer has exclusive access
```

**Pattern: Large File Processing**
```python
# IOChannel for chunked reads with flow control
channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)
channel.set_high_water(65536)  # 64KB chunks

def on_chunk(done, data, error):
    process_chunk(data)
    if done:
        signal_complete()

channel.read(file_size, on_chunk)
```

**Pattern: Event Loop Integration**
```python
# ReadSource for non-blocking socket monitoring
def on_readable():
    data = sock.recv(4096)
    handle_data(data)

source = cygcd.ReadSource(sock.fileno(), on_readable)
source.start()
```

### Choosing Between Similar Features

**Queue vs Workloop**
- Use `Queue` for most cases - simpler and sufficient
- Use `Workloop` when priority inversion is a concern (real-time systems, UI responsiveness)

**IOChannel vs read_async/write_async**
- Use `read_async`/`write_async` for simple one-shot operations
- Use `IOChannel` when you need chunked delivery, flow control, or multiple operations on the same file

**Timer vs Queue.after()**
- Use `after()` for one-shot delayed execution
- Use `Timer` for repeating tasks or when you need to cancel/reconfigure

**Group.wait() vs Semaphore**
- Use `Group` when waiting for a known set of tasks to complete
- Use `Semaphore` for producer-consumer patterns or resource limiting

## Core Concepts

### Queues

Queues manage task execution. Serial queues execute one task at a time in FIFO order. Concurrent queues can execute multiple tasks simultaneously.

```python
import cygcd

# Serial queue (default) - tasks run one at a time
serial = cygcd.Queue("com.example.serial")

# Concurrent queue - tasks can run in parallel
concurrent = cygcd.Queue("com.example.concurrent", concurrent=True)

# Global queues (system-managed, concurrent)
high_priority = cygcd.Queue.global_queue(cygcd.QUEUE_PRIORITY_HIGH)
default = cygcd.Queue.global_queue(cygcd.QOS_CLASS_DEFAULT)
background = cygcd.Queue.global_queue(cygcd.QUEUE_PRIORITY_BACKGROUND)
```

### Async and Sync Execution

```python
q = cygcd.Queue("example")
results = []

# Async - returns immediately, task runs later
q.run_async(lambda: results.append("async"))

# Sync - blocks until task completes
q.run_sync(lambda: results.append("sync"))

print(results)  # ['async', 'sync']
```

### Barriers (Reader-Writer Pattern)

Barriers on concurrent queues wait for all previous tasks to complete, execute exclusively, then allow subsequent tasks.

```python
q = cygcd.Queue("rw", concurrent=True)
data = {"value": 0}

def read():
    print(f"Read: {data['value']}")

def write():
    data["value"] += 1
    print(f"Write: {data['value']}")

# Readers can run concurrently
q.run_async(read)
q.run_async(read)

# Writer runs exclusively
q.barrier_async(write)

# More readers after write completes
q.run_async(read)

q.barrier_sync(lambda: None)  # Wait for all
```

### Groups

Groups track completion of multiple tasks across queues.

```python
import cygcd

g = cygcd.Group()
q = cygcd.Queue.global_queue()
results = []

# Submit tasks to the group
for i in range(5):
    g.run_async(q, lambda i=i: results.append(i))

# Wait for all tasks to complete
g.wait()
print(f"Completed: {sorted(results)}")

# Or get notified when done
g.notify(q, lambda: print("All done!"))
```

### Semaphores

Semaphores limit concurrent access to resources.

```python
import time
import cygcd

# Allow 2 concurrent operations
sem = cygcd.Semaphore(2)
q = cygcd.Queue.global_queue()

def limited_task(task_id):
    sem.wait()  # Acquire (blocks if at limit)
    print(f"Task {task_id} running")
    time.sleep(1)
    sem.signal()  # Release

# Only 2 of these will run at a time
for i in range(5):
    q.run_async(lambda i=i: limited_task(i))
```

### Parallel Apply

Execute a function N times in parallel (like a parallel for loop).

```python
import threading
import cygcd

results = []
lock = threading.Lock()

def process(index):
    result = index * index
    with lock:
        results.append(result)

# Execute 10 times in parallel, blocks until complete
cygcd.apply(10, process)

print(sorted(results))  # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

### Delayed Execution

Schedule tasks to run after a delay.

```python
import time
import cygcd

q = cygcd.Queue("timer")
start = time.time()

q.after(0.5, lambda: print(f"Executed after {time.time() - start:.2f}s"))
q.after(1.0, lambda: print(f"Executed after {time.time() - start:.2f}s"))

time.sleep(1.5)
```

### Once (Thread-Safe Initialization)

Execute a callable exactly once, even from multiple threads.

```python
import cygcd

once = cygcd.Once()
initialized = False

def init():
    global initialized
    initialized = True
    print("Initialized!")

# Only prints once, even if called multiple times
once(init)
once(init)
once(init)
```

### Timers

Repeating or one-shot timers using dispatch sources.

```python
import cygcd

count = 0

def tick():
    global count
    count += 1
    print(f"Tick {count}")

# Create a repeating timer (fires every 0.5 seconds)
timer = cygcd.Timer(0.5, tick)
timer.start()

# ... later
timer.cancel()

# One-shot timer (fires once after delay)
one_shot = cygcd.Timer(1.0, lambda: print("Done!"), repeating=False)
one_shot.start()
```

### Signal Handling

Handle Unix signals asynchronously on a dispatch queue.

```python
import os
import signal
import cygcd

def on_signal():
    print("Received SIGUSR1!")

# Disable default handling
signal.signal(signal.SIGUSR1, signal.SIG_IGN)

# Create signal source
source = cygcd.SignalSource(signal.SIGUSR1, on_signal)
source.start()

# Send signal to self
os.kill(os.getpid(), signal.SIGUSR1)

# ... later
source.cancel()
```

### File Descriptor Monitoring

Monitor file descriptors for read/write availability.

```python
import os
import cygcd

r, w = os.pipe()

def on_readable():
    data = os.read(r, 1024)
    print(f"Received: {data}")

# Monitor for readable data
reader = cygcd.ReadSource(r, on_readable)
reader.start()

# Write triggers the handler
os.write(w, b"Hello!")

# ... later
reader.cancel()
```

### Process Monitoring

Monitor processes for lifecycle events.

```python
import subprocess
import cygcd

def on_exit():
    print("Child process exited!")

# Launch a subprocess
proc = subprocess.Popen(["sleep", "1"])

# Monitor for exit
source = cygcd.ProcessSource(proc.pid, on_exit, events=cygcd.PROC_EXIT)
source.start()

# Wait for exit notification
proc.wait()

source.cancel()
```

### Suspend and Resume

Control queue execution.

```python
q = cygcd.Queue("work")

q.suspend()
# Queue accepts tasks but doesn't execute them
q.run_async(lambda: print("Waiting..."))

q.resume()
# Now tasks execute
```

### Inactive Queues

Create queues that don't execute until activated. Useful for batch configuration.

```python
import cygcd

# Create an inactive queue
q = cygcd.Queue("lazy", inactive=True)
print(q.is_inactive)  # True

# Submit work (queued but not executed)
q.run_async(lambda: print("Waiting to run..."))

# Configure the queue while inactive
q.set_target_queue(cygcd.Queue.global_queue())

# Activate to begin execution
q.activate()
print(q.is_inactive)  # False
```

### Main Queue

Access the main thread's queue (useful for GUI apps).

```python
main = cygcd.Queue.main_queue()
main.run_async(update_ui)
```

### Wall Clock Time

Schedule based on wall clock (adjusts for system time changes).

```python
import time
import cygcd

# Schedule 60 seconds from now using wall clock
t = cygcd.walltime(delta_seconds=60)

# Schedule at a specific Unix timestamp
future = time.time() + 3600  # 1 hour from now
t = cygcd.walltime(timestamp=future)
```

### Dispatch Data

Efficient immutable buffers for I/O operations.

```python
import cygcd

# Create from bytes
data = cygcd.Data(b"Hello, World!")
print(len(data))  # 13
print(bytes(data))  # b'Hello, World!'

# Concatenate (returns new Data, originals unchanged)
part1 = cygcd.Data(b"Hello, ")
part2 = cygcd.Data(b"World!")
combined = part1.concat(part2)

# Extract subrange
message = cygcd.Data(b"The quick brown fox")
word = message.subrange(4, 5)  # b"quick"
```

### Async I/O

Non-blocking file read and write operations.

```python
import os
import cygcd

# Async read
fd = os.open("file.txt", os.O_RDONLY)
sem = cygcd.Semaphore(0)

def on_read(data, error):
    if error == 0:
        print(f"Read {len(data)} bytes: {data}")
    sem.signal()

cygcd.read_async(fd, 1024, on_read)
sem.wait()
os.close(fd)

# Async write
fd = os.open("output.txt", os.O_WRONLY | os.O_CREAT, 0o644)

def on_write(remaining, error):
    if error == 0:
        print("Write complete")
    sem.signal()

cygcd.write_async(fd, b"Hello!", on_write)
sem.wait()
os.close(fd)
```

### IOChannel (High-Performance I/O)

IOChannel provides true dispatch_io functionality for high-performance file I/O with automatic chunking and flow control.

```python
import os
import cygcd

# Open file and create channel
fd = os.open("large_file.bin", os.O_RDONLY)
channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)

# Set high water mark for chunked delivery
channel.set_high_water(65536)  # 64KB chunks

chunks = []
sem = cygcd.Semaphore(0)

def on_read(done, data, error):
    if error:
        print(f"Error: {error}")
    if data:
        chunks.append(data)
        print(f"Received {len(data)} bytes")
    if done:
        sem.signal()

# Read up to 10MB
channel.read(10 * 1024 * 1024, on_read)
sem.wait()

# Use barrier to synchronize after multiple operations
channel.barrier(lambda: print("All I/O complete"))

channel.close()
os.close(fd)
```

For random access I/O with offsets:

```python
channel = cygcd.IOChannel(fd, cygcd.IO_RANDOM)
channel.read(1024, handler, offset=4096)  # Read from offset 4096
channel.write(data, handler, offset=8192)  # Write at offset 8192
```

### Workloops

Priority-inversion-avoiding queues for priority-sensitive workloads.

```python
import cygcd

# Create a workloop
wl = cygcd.Workloop("com.example.workloop")

# Submit work (same API as queues)
wl.run_async(lambda: print("Async task"))
wl.run_sync(lambda: print("Sync task"))

# Inactive workloops (cannot submit work until activated)
inactive_wl = cygcd.Workloop("lazy", inactive=True)
inactive_wl.activate()  # Now ready for work
inactive_wl.run_sync(lambda: print("Running!"))
```

## API Reference

### Queue

| Method | Description |
|--------|-------------|
| `Queue(label=None, concurrent=False, ...)` | Create a queue |
| `Queue.global_queue(priority=0)` | Get a global queue |
| `Queue.main_queue()` | Get the main queue |
| `run_async(func)` | Submit for async execution |
| `run_sync(func)` | Submit and wait for completion |
| `barrier_async(func)` | Async barrier (concurrent queues) |
| `barrier_sync(func)` | Sync barrier |
| `after(delay_seconds, func)` | Delayed execution |
| `suspend()` | Suspend queue execution |
| `resume()` | Resume queue execution |
| `activate()` | Activate an inactive queue |
| `set_target_queue(queue)` | Set target queue for hierarchy |
| `set_context(value, finalizer=None)` | Attach context data to queue |
| `get_context()` | Retrieve context data |
| `set_specific(key, value)` | Set queue-specific data |
| `get_specific(key)` | Get queue-specific data |
| `label` | Queue's label (property) |
| `is_inactive` | Check if queue is inactive (property) |

Queue constructor parameters:
- `label`: Optional string label for debugging
- `concurrent`: If True, create a concurrent queue
- `qos`: Quality of Service class (QOS_CLASS_* constants)
- `relative_priority`: Priority offset within QOS class (-15 to 0)
- `target`: Target queue for queue hierarchy
- `inactive`: If True, create in inactive state (must call activate())

### Group

| Method | Description |
|--------|-------------|
| `Group()` | Create a group |
| `run_async(queue, func)` | Submit task to group |
| `wait(timeout=-1)` | Wait for completion (returns bool) |
| `notify(queue, func)` | Callback when group completes |
| `enter()` | Manually increment task count |
| `leave()` | Manually decrement task count |

### Semaphore

| Method | Description |
|--------|-------------|
| `Semaphore(value)` | Create with initial value |
| `wait(timeout=-1)` | Decrement, block if zero (returns bool) |
| `signal()` | Increment, wake waiters (returns bool) |

### Once

| Method | Description |
|--------|-------------|
| `Once()` | Create a once token |
| `__call__(func)` | Execute func exactly once |

### Timer

| Method | Description |
|--------|-------------|
| `Timer(interval, handler, queue=None, ...)` | Create a timer |
| `start()` | Start the timer |
| `cancel()` | Cancel the timer |
| `set_timer(interval, start_delay, ...)` | Reconfigure the timer |
| `is_cancelled` | Check if cancelled (property) |

Timer constructor parameters:
- `interval`: Seconds between firings
- `handler`: Callable to invoke
- `queue`: Target queue (default: global)
- `start_delay`: Initial delay (default: 0)
- `leeway`: Power optimization leeway (default: 0)
- `repeating`: True for repeating, False for one-shot

### SignalSource

| Method | Description |
|--------|-------------|
| `SignalSource(signum, handler, queue=None)` | Create a signal source |
| `start()` | Start monitoring |
| `cancel()` | Stop monitoring |
| `signal` | Signal number (property) |
| `count` | Signals received since last handler (property) |
| `is_cancelled` | Check if cancelled (property) |

### ReadSource

| Method | Description |
|--------|-------------|
| `ReadSource(fd, handler, queue=None)` | Create a read source |
| `start()` | Start monitoring |
| `cancel()` | Stop monitoring |
| `fd` | File descriptor (property) |
| `bytes_available` | Estimated bytes available (property) |
| `is_cancelled` | Check if cancelled (property) |

### WriteSource

| Method | Description |
|--------|-------------|
| `WriteSource(fd, handler, queue=None)` | Create a write source |
| `start()` | Start monitoring |
| `cancel()` | Stop monitoring |
| `fd` | File descriptor (property) |
| `buffer_space` | Estimated buffer space (property) |
| `is_cancelled` | Check if cancelled (property) |

### ProcessSource

| Method | Description |
|--------|-------------|
| `ProcessSource(pid, handler, events=PROC_EXIT, queue=None)` | Create a process source |
| `start()` | Start monitoring |
| `cancel()` | Stop monitoring |
| `pid` | Process ID (property) |
| `events_pending` | Events that occurred (property) |
| `is_cancelled` | Check if cancelled (property) |

### Data

| Method | Description |
|--------|-------------|
| `Data(bytes=None)` | Create from bytes (or empty) |
| `concat(other)` | Concatenate with another Data |
| `subrange(offset, length)` | Extract a subrange |
| `copy_region(location)` | Get contiguous region at location |
| `apply(func)` | Iterate over contiguous regions |
| `size` | Size in bytes (property) |
| `__len__()` | Size in bytes |
| `__bytes__()` | Convert to bytes |

### Workloop

| Method | Description |
|--------|-------------|
| `Workloop(label, inactive=False)` | Create a workloop |
| `run_async(func)` | Submit for async execution |
| `run_sync(func)` | Submit and wait for completion |
| `activate()` | Activate an inactive workloop |
| `set_autorelease_frequency(freq)` | Set autorelease pool drain frequency |
| `is_inactive` | Check if inactive (property) |

Note: Work cannot be submitted to inactive workloops (raises RuntimeError).
Note: `set_autorelease_frequency` must be called before `activate()`.

### IOChannel

| Method | Description |
|--------|-------------|
| `IOChannel(fd, io_type=IO_STREAM, queue=None, cleanup_handler=None)` | Create I/O channel |
| `read(length, handler, offset=0, queue=None)` | Async read |
| `write(data, handler, offset=0, queue=None)` | Async write |
| `close(stop=False)` | Close channel (stop=True cancels pending) |
| `set_high_water(size)` | Max bytes per handler call |
| `set_low_water(size)` | Min bytes before handler call |
| `set_interval(interval_ns, flags=0)` | Delivery batching interval |
| `barrier(handler)` | Execute after pending I/O completes |
| `fd` | File descriptor (property) |
| `is_closed` | Check if closed (property) |

IOChannel constructor parameters:
- `fd`: File descriptor (must remain open while channel is active)
- `io_type`: `IO_STREAM` (sequential) or `IO_RANDOM` (random access with offsets)
- `queue`: Queue for cleanup handler execution
- `cleanup_handler`: Optional `callable(error: int)` called when channel fully closes

IOChannel callbacks:
- Read/write handlers receive `(done: bool, data: bytes, error: int)`
- `done=True` indicates operation complete; handler won't be called again
- Barrier handlers receive no arguments

### Functions

| Function | Description |
|----------|-------------|
| `apply(iterations, func, queue=None)` | Parallel for loop |
| `time_from_now(seconds)` | Create dispatch time (monotonic) |
| `walltime(timestamp=0, delta_seconds=0)` | Create dispatch time (wall clock) |
| `read_async(fd, length, callback, queue=None)` | Async file read |
| `write_async(fd, data, callback, queue=None)` | Async file write |
| `get_specific(key)` | Get queue-specific data from current queue |

Async I/O callbacks receive `(data, error)` where `error` is 0 on success.

### Constants

**Time:**
- `DISPATCH_TIME_NOW`, `DISPATCH_TIME_FOREVER`
- `NSEC_PER_SEC`, `NSEC_PER_MSEC`, `NSEC_PER_USEC`
- `USEC_PER_SEC`, `MSEC_PER_SEC`

**Queue Priority:**
- `QUEUE_PRIORITY_HIGH`, `QUEUE_PRIORITY_DEFAULT`
- `QUEUE_PRIORITY_LOW`, `QUEUE_PRIORITY_BACKGROUND`

**QOS Classes:**
- `QOS_CLASS_USER_INTERACTIVE`, `QOS_CLASS_USER_INITIATED`
- `QOS_CLASS_DEFAULT`, `QOS_CLASS_UTILITY`
- `QOS_CLASS_BACKGROUND`, `QOS_CLASS_UNSPECIFIED`

**Process Events:**
- `PROC_EXIT` - Process exited
- `PROC_FORK` - Process forked
- `PROC_EXEC` - Process executed exec()
- `PROC_SIGNAL` - Process received a signal

**I/O Types:**
- `IO_STREAM` - Stream-based I/O (sequential)
- `IO_RANDOM` - Random access I/O (with offsets)
- `IO_STOP` - Close flag to cancel pending operations

**Autorelease Frequency (Workloop):**
- `AUTORELEASE_FREQUENCY_INHERIT` - Inherit from target queue
- `AUTORELEASE_FREQUENCY_WORK_ITEM` - Drain after each work item
- `AUTORELEASE_FREQUENCY_NEVER` - Never drain automatically

## Examples

See the `examples/` directory for complete examples:

- `serial_queue.py` - Serial FIFO execution
- `concurrent_queue.py` - Concurrent queue with barriers
- `semaphore.py` - Resource limiting
- `dispatch_once.py` - One-time initialization
- `gcd_groups.py` - Task groups and notifications
- `parallel_apply.py` - Parallel loop execution
- `producer_consumer.py` - Semaphore coordination
- `delayed_execution.py` - Scheduled tasks
- `timer.py` - Repeating and one-shot timers
- `signal_source.py` - Unix signal handling
- `fd_source.py` - File descriptor I/O monitoring
- `process_source.py` - Process lifecycle monitoring
- `inactive_queue.py` - Creating and activating inactive queues
- `dispatch_data.py` - Buffer management with Data objects
- `async_io.py` - Asynchronous file read/write
- `workloop.py` - Priority-inversion-avoiding workloops
- `io_channel.py` - High-performance I/O with chunking and flow control

## Use Case Guides

See `docs/` for detailed guides on specific use cases:

- `usecase_audio.md` - Audio and MIDI applications (low-latency callbacks, sequencing)
- `usecase_image_video.md` - Image and video processing (parallel batch processing, pipelines)
- `usecase_networking.md` - Networking applications (HTTP clients, connection pools, rate limiting)

## Notes

- All GCD operations release the Python GIL, enabling true parallelism
- Callbacks are executed with the GIL held (Python code is thread-safe)
- Global queues are system-managed and should not be released
- Avoid `run_sync()` on a serial queue from within that queue (deadlock)

## License

GCD is licensed under the Apache 2.0 license

This library is licensed under the MIT license

