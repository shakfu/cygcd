# Networking Use Case

Guide to using cygcd for concurrent networking applications.

## Relevant Features

| Feature | Networking Use Case |
|---------|---------------------|
| **Queue (concurrent)** | Parallel HTTP requests, connection handling |
| **Queue (serial)** | Rate limiting, request ordering |
| **Group** | Wait for multiple requests to complete |
| **Semaphore** | Connection pool limiting, throttling |
| **Timer** | Timeouts, retry delays, health checks |
| **ReadSource/WriteSource** | Non-blocking socket I/O |

## Examples

### Concurrent HTTP Requests

Fetch multiple URLs in parallel:

```python
import cygcd
import urllib.request

def fetch_urls(urls, max_concurrent=10):
    """Fetch multiple URLs with bounded concurrency."""
    results = {}
    lock = cygcd.Queue("results.lock")  # Serial queue as lock

    # Limit concurrent connections
    conn_semaphore = cygcd.Semaphore(max_concurrent)

    # Concurrent queue for fetching
    fetch_queue = cygcd.Queue("fetch", concurrent=True,
                              qos=cygcd.QOS_CLASS_UTILITY)

    group = cygcd.Group()

    for url in urls:
        def fetch(url=url):
            conn_semaphore.wait()
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    data = resp.read()
                    # Store result safely
                    lock.run_sync(lambda: results.__setitem__(url, data))
            except Exception as e:
                lock.run_sync(lambda: results.__setitem__(url, e))
            finally:
                conn_semaphore.signal()

        group.run_async(fetch_queue, fetch)

    group.wait()
    return results

# Usage
urls = [
    "https://example.com/api/1",
    "https://example.com/api/2",
    "https://example.com/api/3",
]
results = fetch_urls(urls)
```

### Connection Pool

Manage a pool of reusable connections:

```python
import cygcd
from collections import deque

class ConnectionPool:
    def __init__(self, factory, max_size=10):
        self.factory = factory
        self.max_size = max_size
        self.pool = deque()
        self.size = 0

        # Serial queue for thread-safe pool access
        self.queue = cygcd.Queue("pool.manager")

        # Semaphore to limit total connections
        self.available = cygcd.Semaphore(max_size)

    def acquire(self, timeout=-1):
        """Get a connection from the pool."""
        if not self.available.wait(timeout):
            return None  # Timeout

        conn = [None]

        def get_or_create():
            if self.pool:
                conn[0] = self.pool.popleft()
            else:
                conn[0] = self.factory()
                self.size += 1

        self.queue.run_sync(get_or_create)
        return conn[0]

    def release(self, conn):
        """Return a connection to the pool."""
        def return_conn():
            self.pool.append(conn)

        self.queue.run_sync(return_conn)
        self.available.signal()

    def close_all(self):
        """Close all pooled connections."""
        def close():
            while self.pool:
                conn = self.pool.popleft()
                conn.close()
            self.size = 0

        self.queue.run_sync(close)

# Usage with context manager
class PooledConnection:
    def __init__(self, pool):
        self.pool = pool
        self.conn = None

    def __enter__(self):
        self.conn = self.pool.acquire()
        return self.conn

    def __exit__(self, *args):
        if self.conn:
            self.pool.release(self.conn)
```

### Rate-Limited API Client

Respect API rate limits:

```python
import cygcd
import time

class RateLimitedClient:
    def __init__(self, requests_per_second=10):
        self.interval = 1.0 / requests_per_second
        self.last_request = 0

        # Serial queue ensures ordered, rate-limited requests
        self.queue = cygcd.Queue("api.client")

    def request(self, endpoint, callback):
        """Make a rate-limited request."""
        def do_request():
            # Enforce rate limit
            now = time.time()
            wait_time = self.last_request + self.interval - now
            if wait_time > 0:
                time.sleep(wait_time)

            self.last_request = time.time()

            try:
                result = self._make_request(endpoint)
                callback(result, None)
            except Exception as e:
                callback(None, e)

        self.queue.run_async(do_request)

    def request_sync(self, endpoint):
        """Synchronous rate-limited request."""
        result = [None]
        error = [None]
        sem = cygcd.Semaphore(0)

        def on_complete(r, e):
            result[0] = r
            error[0] = e
            sem.signal()

        self.request(endpoint, on_complete)
        sem.wait()

        if error[0]:
            raise error[0]
        return result[0]

    def _make_request(self, endpoint):
        # Actual HTTP request implementation
        import urllib.request
        with urllib.request.urlopen(endpoint) as resp:
            return resp.read()

# Batch requests with rate limiting
client = RateLimitedClient(requests_per_second=5)

endpoints = [f"https://api.example.com/item/{i}" for i in range(100)]
results = []
sem = cygcd.Semaphore(0)
pending = [len(endpoints)]

for endpoint in endpoints:
    def on_result(data, error, ep=endpoint):
        if data:
            results.append((ep, data))
        pending[0] -= 1
        if pending[0] == 0:
            sem.signal()

    client.request(endpoint, on_result)

sem.wait()  # Wait for all to complete
```

### Retry with Exponential Backoff

Handle transient failures:

```python
import cygcd
import random

class RetryClient:
    def __init__(self, max_retries=3, base_delay=1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.queue = cygcd.Queue("retry.client",
                                  qos=cygcd.QOS_CLASS_UTILITY)

    def request_with_retry(self, func, callback):
        """Execute func with retry on failure."""
        attempt = [0]

        def try_request():
            attempt[0] += 1
            try:
                result = func()
                callback(result, None)
            except Exception as e:
                if attempt[0] < self.max_retries:
                    # Calculate delay with jitter
                    delay = self.base_delay * (2 ** (attempt[0] - 1))
                    jitter = random.uniform(0, delay * 0.1)

                    # Schedule retry
                    self.queue.after(delay + jitter, try_request)
                else:
                    callback(None, e)

        self.queue.run_async(try_request)

# Usage
client = RetryClient(max_retries=5, base_delay=0.5)

def fetch_data():
    import urllib.request
    with urllib.request.urlopen("https://api.example.com/data") as resp:
        return resp.read()

sem = cygcd.Semaphore(0)

def on_complete(data, error):
    if error:
        print(f"Failed after retries: {error}")
    else:
        print(f"Success: {len(data)} bytes")
    sem.signal()

client.request_with_retry(fetch_data, on_complete)
sem.wait()
```

### Non-Blocking Socket with ReadSource

Monitor sockets for incoming data:

```python
import cygcd
import socket

class AsyncSocket:
    def __init__(self, sock):
        self.sock = sock
        self.sock.setblocking(False)
        self.fd = sock.fileno()

        self.queue = cygcd.Queue("socket.io",
                                  qos=cygcd.QOS_CLASS_USER_INITIATED)

        self.read_source = None
        self.write_source = None
        self.read_handler = None
        self.write_handler = None

    def on_readable(self, handler):
        """Call handler when socket has data to read."""
        self.read_handler = handler

        def on_read():
            bytes_available = self.read_source.bytes_available
            if bytes_available > 0 and self.read_handler:
                try:
                    data = self.sock.recv(bytes_available)
                    if data:
                        self.read_handler(data, None)
                    else:
                        # Connection closed
                        self.read_handler(None, ConnectionError("closed"))
                except Exception as e:
                    self.read_handler(None, e)

        self.read_source = cygcd.ReadSource(self.fd, on_read, self.queue)
        self.read_source.start()

    def on_writable(self, handler):
        """Call handler when socket can accept writes."""
        self.write_handler = handler

        def on_write():
            if self.write_handler:
                self.write_handler()

        self.write_source = cygcd.WriteSource(self.fd, on_write, self.queue)
        self.write_source.start()

    def stop_read(self):
        if self.read_source:
            self.read_source.cancel()
            self.read_source = None

    def stop_write(self):
        if self.write_source:
            self.write_source.cancel()
            self.write_source = None

    def close(self):
        self.stop_read()
        self.stop_write()
        self.sock.close()

# Example: Simple echo client
def run_echo_client(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    async_sock = AsyncSocket(sock)
    received = []
    done = cygcd.Semaphore(0)

    def on_data(data, error):
        if error:
            print(f"Error: {error}")
            done.signal()
        elif data:
            received.append(data)
            print(f"Received: {data}")

    async_sock.on_readable(on_data)

    # Send some data
    sock.send(b"Hello, server!")

    # Wait for response
    done.wait(5.0)
    async_sock.close()

    return b"".join(received)
```

### Health Check with Timer

Periodic endpoint monitoring:

```python
import cygcd
import urllib.request
import time

class HealthChecker:
    def __init__(self, endpoints, interval=30.0):
        self.endpoints = endpoints
        self.interval = interval
        self.status = {ep: None for ep in endpoints}

        self.queue = cygcd.Queue("health.check",
                                  qos=cygcd.QOS_CLASS_BACKGROUND)
        self.check_queue = cygcd.Queue("health.requests",
                                        concurrent=True)
        self.timer = None
        self.running = False

    def start(self):
        """Start periodic health checks."""
        self.running = True

        def check_all():
            if not self.running:
                return

            group = cygcd.Group()

            for endpoint in self.endpoints:
                def check(ep=endpoint):
                    start = time.time()
                    try:
                        with urllib.request.urlopen(ep, timeout=10) as resp:
                            latency = time.time() - start
                            self.status[ep] = {
                                "healthy": resp.status == 200,
                                "status": resp.status,
                                "latency_ms": latency * 1000,
                                "checked_at": time.time()
                            }
                    except Exception as e:
                        self.status[ep] = {
                            "healthy": False,
                            "error": str(e),
                            "checked_at": time.time()
                        }

                group.run_async(self.check_queue, check)

            group.wait()

        self.timer = cygcd.Timer(
            interval=self.interval,
            handler=check_all,
            queue=self.queue,
            start_delay=0  # Run immediately
        )
        self.timer.start()

    def stop(self):
        """Stop health checks."""
        self.running = False
        if self.timer:
            self.timer.cancel()

    def get_status(self):
        """Get current health status."""
        return dict(self.status)

    def get_healthy(self):
        """Get list of healthy endpoints."""
        return [ep for ep, status in self.status.items()
                if status and status.get("healthy")]

# Usage
checker = HealthChecker([
    "https://api1.example.com/health",
    "https://api2.example.com/health",
    "https://api3.example.com/health",
], interval=60.0)

checker.start()

# Later...
print(checker.get_status())
healthy = checker.get_healthy()

# Cleanup
checker.stop()
```

### Request Timeout with Group

Enforce timeouts on async operations:

```python
import cygcd

def fetch_with_timeout(url, timeout_seconds=30):
    """Fetch URL with timeout."""
    result = [None]
    error = [None]
    timed_out = [False]

    queue = cygcd.Queue("fetch.timeout")
    group = cygcd.Group()

    def do_fetch():
        if timed_out[0]:
            return
        try:
            import urllib.request
            with urllib.request.urlopen(url) as resp:
                result[0] = resp.read()
        except Exception as e:
            error[0] = e

    group.run_async(queue, do_fetch)

    completed = group.wait(timeout_seconds)

    if not completed:
        timed_out[0] = True
        raise TimeoutError(f"Request timed out after {timeout_seconds}s")

    if error[0]:
        raise error[0]

    return result[0]

# Usage
try:
    data = fetch_with_timeout("https://slow-api.example.com/data", timeout_seconds=5)
except TimeoutError:
    print("Request timed out")
except Exception as e:
    print(f"Request failed: {e}")
```

## Patterns

### Fan-Out/Fan-In

Distribute work and collect results:

```python
import cygcd

def fan_out_fan_in(items, process_func, max_concurrent=10):
    """Process items in parallel, collect results."""
    results = [None] * len(items)

    work_queue = cygcd.Queue("work", concurrent=True)
    semaphore = cygcd.Semaphore(max_concurrent)
    group = cygcd.Group()

    for i, item in enumerate(items):
        def process(idx=i, it=item):
            semaphore.wait()
            try:
                results[idx] = process_func(it)
            finally:
                semaphore.signal()

        group.run_async(work_queue, process)

    group.wait()
    return results
```

### Producer-Consumer for Streaming

Process data as it arrives:

```python
import cygcd
from collections import deque

class StreamProcessor:
    def __init__(self, processor, max_buffer=100):
        self.processor = processor
        self.buffer = deque()
        self.max_buffer = max_buffer
        self.running = True

        # Semaphores for bounded buffer
        self.items_available = cygcd.Semaphore(0)
        self.slots_available = cygcd.Semaphore(max_buffer)

        # Queues
        self.buffer_queue = cygcd.Queue("buffer")
        self.process_queue = cygcd.Queue("process",
                                          qos=cygcd.QOS_CLASS_USER_INITIATED)

        # Start consumer
        self.process_queue.run_async(self._consume)

    def push(self, item):
        """Add item to processing queue (blocks if buffer full)."""
        self.slots_available.wait()
        self.buffer_queue.run_sync(lambda: self.buffer.append(item))
        self.items_available.signal()

    def _consume(self):
        """Consumer loop."""
        while self.running:
            if not self.items_available.wait(1.0):
                continue

            item = [None]
            self.buffer_queue.run_sync(
                lambda: item.__setitem__(0, self.buffer.popleft())
            )
            self.slots_available.signal()

            try:
                self.processor(item[0])
            except Exception as e:
                print(f"Processing error: {e}")

    def stop(self):
        self.running = False
```

## Caveats

### GIL Limitations

Python's GIL limits true parallelism for CPU-bound work. GCD excels at:
- I/O-bound operations (network, file)
- Waiting on external resources
- Coordinating between threads

For CPU-bound work, consider `multiprocessing` or releasing GIL in C extensions.

### Socket Compatibility

`ReadSource`/`WriteSource` work with file descriptors. Ensure:
- Sockets are in non-blocking mode
- You handle `EAGAIN`/`EWOULDBLOCK` appropriately
- macOS kqueue is being used (automatic with GCD)

### Memory Pressure

With many concurrent connections:
- Use semaphores to limit concurrency
- Implement connection pooling
- Monitor memory usage

### Timeout Accuracy

GCD timers have ~1ms precision. For network timeouts:
- This is usually sufficient for seconds-level timeouts
- For sub-millisecond precision, use other mechanisms
