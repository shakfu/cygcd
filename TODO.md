# TODO

## API Coverage

- [x] Queues (serial, concurrent, global, main, inactive, QOS, target hierarchy)
- [x] Execution (async, sync, barrier, after, apply)
- [x] Groups (async, wait, notify, enter/leave)
- [x] Semaphores
- [x] Once
- [x] Time (dispatch_time, walltime)
- [x] Timer
- [x] Dispatch Sources (Signal, Read, Write, Process)
- [x] Dispatch Data (create, concat, subrange, copy_region, apply)
- [x] Dispatch I/O (read_async, write_async, IOChannel)
- [x] Workloops (with autorelease frequency)
- [x] Queue context and queue-specific data

## Not Wrapped (By Design)

- **Block APIs** - Not applicable; Python uses callables
- **Debug/Introspection** - Development-only (`dispatch_debug`, `dispatch_assert_queue`, etc.)
- **Deprecated** - `dispatch_get_current_queue`
