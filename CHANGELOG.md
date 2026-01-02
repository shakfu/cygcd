# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3]

### Added

#### Queue Context and Specific Data

- `Queue.set_context(value, finalizer)` - Attach arbitrary context data to a queue
- `Queue.get_context()` - Retrieve context data from a queue
- `Queue.set_specific(key, value)` - Set queue-specific data (thread-local-like storage)
- `Queue.get_specific(key)` - Get queue-specific data from a queue
- `get_specific(key)` - Get queue-specific data from the current queue

#### Data Methods

- `Data.copy_region(location)` - Get contiguous region containing a location
- `Data.apply(func)` - Iterate over contiguous regions of data

#### Workloop Enhancements

- `Workloop.set_autorelease_frequency(frequency)` - Configure autorelease pool drain frequency
- `AUTORELEASE_FREQUENCY_INHERIT` - Inherit from target queue
- `AUTORELEASE_FREQUENCY_WORK_ITEM` - Drain after each work item
- `AUTORELEASE_FREQUENCY_NEVER` - Never drain automatically

## [0.1.2]

### Added

#### High-Performance Async I/O

- `IOChannel` - Dispatch I/O channel for high-performance async file operations
  - `IOChannel(fd, io_type, queue, cleanup_handler)` - Create channel from file descriptor
  - `read(length, handler, offset, queue)` - Async read with chunked delivery
  - `write(data, handler, offset, queue)` - Async write with progress callbacks
  - `close(stop)` - Close channel, optionally cancelling pending operations
  - `set_high_water(size)` - Set maximum bytes per handler callback
  - `set_low_water(size)` - Set minimum bytes before handler is called
  - `set_interval(interval_ns, strict)` - Set delivery interval for chunked I/O
  - `barrier(handler, queue)` - Execute handler after all pending I/O completes
  - `fd` property - File descriptor associated with channel
  - Supports both `IO_STREAM` (sequential) and `IO_RANDOM` (random access) modes

#### Constants

- `IO_STOP` - Flag for `IOChannel.close()` to cancel pending operations

#### Documentation

- `docs/usecase_audio.md` - Guide for audio and MIDI applications
  - Low-latency audio callbacks with Timer and QOS
  - MIDI sequencing and clock generation
  - Multi-track synchronized playback
  - Lookahead scheduling patterns
  - Priority inversion avoidance with Workloop

- `docs/usecase_image_video.md` - Guide for image and video processing
  - Parallel image batch processing
  - Video frame pipelines
  - Thumbnail generation
  - Real-time video effects

- README feature comparison table with usage guidance

#### Examples

- `examples/io_channel.py` - IOChannel usage for chunked file I/O

#### Technical

- Objective-C block support for dispatch_io APIs
- Block-to-Python callback bridge with proper lifecycle management

## [0.1.1]

### Added

#### Dispatch Sources

- `SignalSource` - Monitor Unix signals asynchronously
  - `start()` / `cancel()` - Control signal monitoring
  - `signal` property - Signal number being monitored
  - `count` property - Signals received since last handler
  - `is_cancelled` property - Check cancellation status

- `ReadSource` - Monitor file descriptors for read availability
  - `start()` / `cancel()` - Control monitoring
  - `fd` property - File descriptor being monitored
  - `bytes_available` property - Estimated bytes available
  - `is_cancelled` property - Check cancellation status

- `WriteSource` - Monitor file descriptors for write availability
  - `start()` / `cancel()` - Control monitoring
  - `fd` property - File descriptor being monitored
  - `buffer_space` property - Estimated buffer space
  - `is_cancelled` property - Check cancellation status

- `ProcessSource` - Monitor process lifecycle events
  - `start()` / `cancel()` - Control monitoring
  - `pid` property - Process ID being monitored
  - `events_pending` property - Events that occurred
  - `is_cancelled` property - Check cancellation status
  - Supports `PROC_EXIT`, `PROC_FORK`, `PROC_EXEC`, `PROC_SIGNAL` events

#### Queue Enhancements

- `Queue` now supports Quality of Service (QOS) attributes
  - `qos` parameter - Set QOS class at creation
  - `relative_priority` parameter - Priority offset within QOS class

- `Queue` now supports target queue hierarchy
  - `target` parameter - Set target queue at creation
  - `set_target_queue(queue)` method - Set target queue after creation

#### Inactive Queues

- `Queue` now supports inactive state
  - `inactive` parameter - Create queue in inactive state
  - `activate()` method - Activate an inactive queue
  - `is_inactive` property - Check if queue is inactive

#### Dispatch Data

- `Data` - Efficient immutable buffer for I/O operations
  - `Data(bytes)` - Create from bytes
  - `concat(other)` - Concatenate two Data objects
  - `subrange(offset, length)` - Extract a subrange
  - `size` property - Get data size
  - `__len__` / `__bytes__` - Python protocol support

#### Dispatch I/O Convenience

- `read_async(fd, length, callback, queue)` - Asynchronous file read
- `write_async(fd, data, callback, queue)` - Asynchronous file write

#### Workloops

- `Workloop` - Priority-inversion-avoiding execution
  - `run_async(func)` - Asynchronous task execution
  - `run_sync(func)` - Synchronous task execution
  - `activate()` - Activate an inactive workloop
  - `is_inactive` property - Check activation status
  - Note: Work cannot be submitted to inactive workloops

#### Constants

- Process event flags: `PROC_EXIT`, `PROC_FORK`, `PROC_EXEC`, `PROC_SIGNAL`
- I/O type constants: `IO_STREAM`, `IO_RANDOM`

#### Examples

- `signal_source.py` - Unix signal handling with dispatch sources
- `fd_source.py` - File descriptor I/O monitoring
- `process_source.py` - Process lifecycle monitoring
- `inactive_queue.py` - Creating and activating inactive queues
- `dispatch_data.py` - Buffer management with Data objects
- `async_io.py` - Asynchronous file read/write operations
- `workloop.py` - Priority-inversion-avoiding workloops

---

## [0.1.0]

### Added

- Initial release of cygcd - Python wrapper for macOS Grand Central Dispatch

#### Core Classes

- `Queue` - Dispatch queue wrapper (serial and concurrent)
  - `run_async(func)` - Asynchronous task execution
  - `run_sync(func)` - Synchronous task execution
  - `barrier_async(func)` - Barrier for concurrent queues (async)
  - `barrier_sync(func)` - Barrier for concurrent queues (sync)
  - `after(delay, func)` - Delayed task execution
  - `global_queue(priority)` - Access to system global queues
  - `main_queue()` - Access to main thread queue
  - `suspend()` / `resume()` - Queue execution control
  - `label` property - Queue label for debugging

- `Group` - Track completion of multiple tasks
  - `run_async(queue, func)` - Submit task to group
  - `wait(timeout)` - Wait for all tasks to complete
  - `notify(queue, func)` - Notification when group completes
  - `enter()` / `leave()` - Manual task tracking

- `Semaphore` - Counting semaphore for resource limiting
  - `wait(timeout)` - Decrement semaphore (block if zero)
  - `signal()` - Increment semaphore

- `Once` - Thread-safe one-time execution

- `Timer` - Dispatch source timer
  - `start()` - Start the timer
  - `cancel()` - Cancel the timer
  - `set_timer(interval, ...)` - Reconfigure timer parameters
  - `is_cancelled` property - Check cancellation status
  - Supports repeating and one-shot timers
  - Configurable leeway for power optimization

#### Functions

- `apply(iterations, func, queue)` - Parallel for loop
- `time_from_now(seconds)` - Create dispatch time (monotonic clock)
- `walltime(timestamp, delta_seconds)` - Create dispatch time (wall clock)

#### Constants

- Time constants: `DISPATCH_TIME_NOW`, `DISPATCH_TIME_FOREVER`, `NSEC_PER_SEC`, etc.
- Queue priorities: `QUEUE_PRIORITY_HIGH`, `QUEUE_PRIORITY_DEFAULT`, `QUEUE_PRIORITY_LOW`, `QUEUE_PRIORITY_BACKGROUND`
- QOS classes: `QOS_CLASS_USER_INTERACTIVE`, `QOS_CLASS_USER_INITIATED`, `QOS_CLASS_DEFAULT`, `QOS_CLASS_UTILITY`, `QOS_CLASS_BACKGROUND`

#### Examples

- `serial_queue.py` - Serial FIFO execution
- `concurrent_queue.py` - Concurrent queue with barriers
- `semaphore.py` - Resource limiting with semaphores
- `dispatch_once.py` - One-time initialization
- `gcd_groups.py` - Task groups and notifications
- `parallel_apply.py` - Parallel loop execution
- `producer_consumer.py` - Semaphore-based coordination
- `delayed_execution.py` - Scheduled delayed tasks

#### Technical

- All GCD operations release the Python GIL via `nogil` for true parallelism
- Proper reference counting for dispatch objects
- Trampoline callbacks that safely acquire GIL for Python execution
