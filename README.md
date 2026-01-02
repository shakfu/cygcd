# pygcd

Python wrapper for Apple's Grand Central Dispatch (GCD) framework on macOS.

GCD provides a powerful API for concurrent programming, allowing you to execute tasks asynchronously on system-managed thread pools. This wrapper exposes the core GCD primitives to Python with proper GIL handling for true parallelism.

## Installation

```bash
# Clone and install
git clone <repository>
cd pygcd
make
```

Requires macOS and Python 3.9+.

## Quick Start

```python
import pygcd

# Create a serial queue
q = pygcd.Queue("com.example.myqueue")

# Execute tasks asynchronously
q.run_async(lambda: print("Hello from GCD!"))

# Execute synchronously (blocks until complete)
q.run_sync(lambda: print("This runs and waits"))
```

## Core Concepts

### Queues

Queues manage task execution. Serial queues execute one task at a time in FIFO order. Concurrent queues can execute multiple tasks simultaneously.

```python
import pygcd

# Serial queue (default) - tasks run one at a time
serial = pygcd.Queue("com.example.serial")

# Concurrent queue - tasks can run in parallel
concurrent = pygcd.Queue("com.example.concurrent", concurrent=True)

# Global queues (system-managed, concurrent)
high_priority = pygcd.Queue.global_queue(pygcd.QUEUE_PRIORITY_HIGH)
default = pygcd.Queue.global_queue(pygcd.QOS_CLASS_DEFAULT)
background = pygcd.Queue.global_queue(pygcd.QUEUE_PRIORITY_BACKGROUND)
```

### Async and Sync Execution

```python
q = pygcd.Queue("example")
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
q = pygcd.Queue("rw", concurrent=True)
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
import pygcd

g = pygcd.Group()
q = pygcd.Queue.global_queue()
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
import pygcd

# Allow 2 concurrent operations
sem = pygcd.Semaphore(2)
q = pygcd.Queue.global_queue()

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
import pygcd

results = []
lock = threading.Lock()

def process(index):
    result = index * index
    with lock:
        results.append(result)

# Execute 10 times in parallel, blocks until complete
pygcd.apply(10, process)

print(sorted(results))  # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

### Delayed Execution

Schedule tasks to run after a delay.

```python
import time
import pygcd

q = pygcd.Queue("timer")
start = time.time()

q.after(0.5, lambda: print(f"Executed after {time.time() - start:.2f}s"))
q.after(1.0, lambda: print(f"Executed after {time.time() - start:.2f}s"))

time.sleep(1.5)
```

### Once (Thread-Safe Initialization)

Execute a callable exactly once, even from multiple threads.

```python
import pygcd

once = pygcd.Once()
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
import pygcd

count = 0

def tick():
    global count
    count += 1
    print(f"Tick {count}")

# Create a repeating timer (fires every 0.5 seconds)
timer = pygcd.Timer(0.5, tick)
timer.start()

# ... later
timer.cancel()

# One-shot timer (fires once after delay)
one_shot = pygcd.Timer(1.0, lambda: print("Done!"), repeating=False)
one_shot.start()
```

### Signal Handling

Handle Unix signals asynchronously on a dispatch queue.

```python
import os
import signal
import pygcd

def on_signal():
    print("Received SIGUSR1!")

# Disable default handling
signal.signal(signal.SIGUSR1, signal.SIG_IGN)

# Create signal source
source = pygcd.SignalSource(signal.SIGUSR1, on_signal)
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
import pygcd

r, w = os.pipe()

def on_readable():
    data = os.read(r, 1024)
    print(f"Received: {data}")

# Monitor for readable data
reader = pygcd.ReadSource(r, on_readable)
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
import pygcd

def on_exit():
    print("Child process exited!")

# Launch a subprocess
proc = subprocess.Popen(["sleep", "1"])

# Monitor for exit
source = pygcd.ProcessSource(proc.pid, on_exit, events=pygcd.PROC_EXIT)
source.start()

# Wait for exit notification
proc.wait()

source.cancel()
```

### Suspend and Resume

Control queue execution.

```python
q = pygcd.Queue("work")

q.suspend()
# Queue accepts tasks but doesn't execute them
q.run_async(lambda: print("Waiting..."))

q.resume()
# Now tasks execute
```

### Main Queue

Access the main thread's queue (useful for GUI apps).

```python
main = pygcd.Queue.main_queue()
main.run_async(update_ui)
```

### Wall Clock Time

Schedule based on wall clock (adjusts for system time changes).

```python
import time
import pygcd

# Schedule 60 seconds from now using wall clock
t = pygcd.walltime(delta_seconds=60)

# Schedule at a specific Unix timestamp
future = time.time() + 3600  # 1 hour from now
t = pygcd.walltime(timestamp=future)
```

## API Reference

### Queue

| Method | Description |
|--------|-------------|
| `Queue(label=None, concurrent=False, qos=0, target=None)` | Create a queue |
| `Queue.global_queue(priority=0)` | Get a global queue |
| `Queue.main_queue()` | Get the main queue |
| `run_async(func)` | Submit for async execution |
| `run_sync(func)` | Submit and wait for completion |
| `barrier_async(func)` | Async barrier (concurrent queues) |
| `barrier_sync(func)` | Sync barrier |
| `after(delay_seconds, func)` | Delayed execution |
| `suspend()` | Suspend queue execution |
| `resume()` | Resume queue execution |
| `set_target_queue(queue)` | Set target queue for hierarchy |
| `label` | Queue's label (property) |

Queue constructor parameters:
- `label`: Optional string label for debugging
- `concurrent`: If True, create a concurrent queue
- `qos`: Quality of Service class (QOS_CLASS_* constants)
- `relative_priority`: Priority offset within QOS class (-15 to 0)
- `target`: Target queue for queue hierarchy

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

### Functions

| Function | Description |
|----------|-------------|
| `apply(iterations, func, queue=None)` | Parallel for loop |
| `time_from_now(seconds)` | Create dispatch time (monotonic) |
| `walltime(timestamp=0, delta_seconds=0)` | Create dispatch time (wall clock) |

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

## Notes

- All GCD operations release the Python GIL, enabling true parallelism
- Callbacks are executed with the GIL held (Python code is thread-safe)
- Global queues are system-managed and should not be released
- Avoid `run_sync()` on a serial queue from within that queue (deadlock)

## License

Apache 2.0
