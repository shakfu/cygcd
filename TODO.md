# TODO - GCD API Wrapping Plan

Prioritized plan for wrapping remaining Grand Central Dispatch APIs.

## Current Coverage

- [x] Queues (create, global, main, label, suspend/resume, target, QOS)
- [x] Execution (async, sync, barrier, after, apply)
- [x] Groups (create, async, wait, notify, enter/leave)
- [x] Semaphores (create, wait, signal)
- [x] Once
- [x] Time (dispatch_time, dispatch_walltime)
- [x] Timer (dispatch source)
- [x] SignalSource (dispatch source for signals)
- [x] ReadSource/WriteSource (dispatch source for file descriptors)
- [x] ProcessSource (dispatch source for process events)

---

## Phase 1: High Priority - COMPLETED

Core functionality that unlocks common use cases.

### 1.1 Dispatch Sources - Timers - DONE

Event-driven timers are one of the most useful GCD features.

```python
# Implemented API
timer = pygcd.Timer(interval=1.0, handler=on_tick, queue=q)
timer.start()
timer.cancel()
```

Functions wrapped:
- [x] `dispatch_source_create` (with `DISPATCH_SOURCE_TYPE_TIMER`)
- [x] `dispatch_source_set_timer`
- [x] `dispatch_source_set_event_handler_f`
- [x] `dispatch_source_cancel`
- [x] `dispatch_resume` (sources start suspended)

### 1.2 Queue Suspend/Resume - DONE

Control queue execution for resource management.

```python
q.suspend()
# ... queue tasks but don't execute
q.resume()
```

Functions wrapped:
- [x] `dispatch_suspend`
- [x] `dispatch_resume`

### 1.3 Main Queue Access - DONE

Required for GUI applications and main-thread callbacks.

```python
main = pygcd.Queue.main_queue()
main.run_async(update_ui)
```

Functions wrapped:
- [x] `dispatch_get_main_queue`

Note: `dispatch_main()` conflicts with Python's event loop - document alternatives.

### 1.4 Wall Clock Time - DONE

Schedule tasks at absolute times.

```python
t = pygcd.walltime(timestamp=time.time(), delta_seconds=60)
```

Functions wrapped:
- [x] `dispatch_walltime`

---

## Phase 2: Medium Priority - COMPLETED

Advanced features for specialized use cases.

### 2.1 Dispatch Sources - Signals - DONE

Handle Unix signals asynchronously.

```python
sig = pygcd.SignalSource(signal.SIGINT, handler=on_interrupt, queue=q)
sig.start()
```

Functions wrapped:
- [x] `dispatch_source_create` (with `DISPATCH_SOURCE_TYPE_SIGNAL`)
- [x] `dispatch_source_get_data`
- [x] `dispatch_source_get_handle`

### 2.2 Dispatch Sources - File Descriptors - DONE

Monitor file descriptors for read/write readiness.

```python
reader = pygcd.ReadSource(fd, handler=on_readable, queue=q)
writer = pygcd.WriteSource(fd, handler=on_writable, queue=q)
```

Functions wrapped:
- [x] `dispatch_source_create` (with `DISPATCH_SOURCE_TYPE_READ`, `_WRITE`)

### 2.3 Dispatch Sources - Process Events - DONE

Monitor process lifecycle events.

```python
proc = pygcd.ProcessSource(pid, handler=on_exit, events=pygcd.PROC_EXIT, queue=q)
```

Functions wrapped:
- [x] `dispatch_source_create` (with `DISPATCH_SOURCE_TYPE_PROC`)
- [x] `dispatch_source_get_mask`

### 2.4 Queue Target/Hierarchy - DONE

Create queue hierarchies for priority management.

```python
parent = pygcd.Queue("parent")
child = pygcd.Queue("child", target=parent)
```

Functions wrapped:
- [x] `dispatch_set_target_queue`

### 2.5 Queue QOS Attributes - DONE

Fine-grained quality of service control.

```python
q = pygcd.Queue("work", qos=pygcd.QOS_CLASS_UTILITY)
```

Functions wrapped:
- [x] `dispatch_queue_attr_make_with_qos_class`

---

## Phase 3: Lower Priority

Specialized APIs with narrower use cases.

### 3.1 Dispatch I/O - Channels

High-performance async file I/O.

```python
channel = pygcd.IOChannel(fd, queue=q)
channel.read(length, handler=on_data)
channel.write(data, handler=on_complete)
channel.close()
```

Functions to wrap:
- [ ] `dispatch_io_create`
- [ ] `dispatch_io_read`
- [ ] `dispatch_io_write`
- [ ] `dispatch_io_close`
- [ ] `dispatch_io_set_high_water`
- [ ] `dispatch_io_set_low_water`
- [ ] `dispatch_io_set_interval`
- [ ] `dispatch_io_barrier`

### 3.2 Dispatch I/O - Convenience

Simple async file operations.

```python
pygcd.read_fd(fd, queue=q, handler=on_data)
pygcd.write_fd(fd, data, queue=q, handler=on_complete)
```

Functions to wrap:
- [ ] `dispatch_read`
- [ ] `dispatch_write`

### 3.3 Dispatch Data

Efficient buffer management for I/O.

```python
data = pygcd.Data(bytes_obj)
combined = data.concat(other_data)
region = data.subrange(offset, length)
```

Functions to wrap:
- [ ] `dispatch_data_create`
- [ ] `dispatch_data_get_size`
- [ ] `dispatch_data_create_concat`
- [ ] `dispatch_data_create_subrange`
- [ ] `dispatch_data_create_map`
- [ ] `dispatch_data_copy_region`
- [ ] `dispatch_data_apply`

### 3.4 Inactive Queues

Create queues that don't start until activated.

```python
q = pygcd.Queue("lazy", inactive=True)
# configure queue...
q.activate()
```

Functions to wrap:
- [ ] `dispatch_queue_attr_make_initially_inactive`
- [ ] `dispatch_activate`

### 3.5 Workloops

Priority-inversion-avoiding queues.

```python
wl = pygcd.Workloop("priority-work")
```

Functions to wrap:
- [ ] `dispatch_workloop_create`
- [ ] `dispatch_workloop_create_inactive`
- [ ] `dispatch_workloop_set_autorelease_frequency`

### 3.6 Object Context

Attach context data to dispatch objects.

```python
q.set_context(my_data)
q.set_finalizer(cleanup_func)
data = q.get_context()
```

Functions to wrap:
- [ ] `dispatch_set_context`
- [ ] `dispatch_get_context`
- [ ] `dispatch_set_finalizer_f`

### 3.7 Queue-Specific Data

Thread-local-like storage for queues.

```python
q.set_specific(key, value)
value = pygcd.get_specific(key)  # from current queue
```

Functions to wrap:
- [ ] `dispatch_queue_set_specific`
- [ ] `dispatch_queue_get_specific`
- [ ] `dispatch_get_specific`

---

## Phase 4: Low Priority / Won't Wrap

### 4.1 Block APIs

Not applicable - Python uses callables.

- `dispatch_block_create`
- `dispatch_block_create_with_qos_class`
- `dispatch_block_perform`
- `dispatch_block_wait`
- `dispatch_block_notify`
- `dispatch_block_cancel`
- `dispatch_block_testcancel`

### 4.2 Debug/Introspection

Development-only, not needed for production.

- `dispatch_debug`
- `dispatch_debugv`
- `dispatch_assert_queue`
- `dispatch_assert_queue_barrier`
- `dispatch_assert_queue_not`
- `dispatch_introspection_*`

### 4.3 Deprecated

- `dispatch_get_current_queue` (deprecated)

---

## Implementation Notes

### Callback Pattern

All `_f` variants use function pointers. The pattern established:

```cython
cdef void _trampoline(void* ctx) noexcept with gil:
    func = <object>ctx
    try:
        func()
    except:
        PyErr_Print()
    finally:
        Py_DECREF(func)
```

### Source Pattern

Sources require:
1. Create with `dispatch_source_create`
2. Set handler with `dispatch_source_set_event_handler_f`
3. Resume with `dispatch_resume` (sources start suspended)
4. Cancel with `dispatch_source_cancel`

### Memory Management

- Created objects: `_owned = True`, release in `__dealloc__`
- Global objects: `_owned = False`, never release
- Sources: must cancel before release

---

## Testing Requirements

Each new feature needs:
- [ ] Unit tests for basic functionality
- [ ] Tests for error conditions
- [ ] Tests for edge cases (timeouts, cancellation)
- [ ] Example script demonstrating usage
