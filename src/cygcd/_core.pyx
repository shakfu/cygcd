# cython: language_level=3
"""
cygcd - Python wrapper for macOS Grand Central Dispatch (GCD).

Provides Python bindings to Apple's GCD framework for concurrent programming.
"""

from libc.stdint cimport uint64_t, int64_t, intptr_t, uintptr_t
from posix.types cimport off_t
from cpython.ref cimport PyObject, Py_INCREF, Py_DECREF
from cpython.exc cimport PyErr_Occurred, PyErr_Print

# Time constants
DEF NSEC_PER_SEC = 1000000000
DEF NSEC_PER_MSEC = 1000000
DEF NSEC_PER_USEC = 1000
DEF USEC_PER_SEC = 1000000
DEF MSEC_PER_SEC = 1000

# Export time constants to Python
NSEC_PER_SEC_PY = NSEC_PER_SEC
NSEC_PER_MSEC_PY = NSEC_PER_MSEC
NSEC_PER_USEC_PY = NSEC_PER_USEC
USEC_PER_SEC_PY = USEC_PER_SEC
MSEC_PER_SEC_PY = MSEC_PER_SEC

# Time special values (DISPATCH_TIME_FOREVER is ~0ULL = 0xFFFFFFFFFFFFFFFF)
DEF _DISPATCH_TIME_NOW = 0
DEF _DISPATCH_TIME_FOREVER = 0xFFFFFFFFFFFFFFFF

DISPATCH_TIME_NOW = _DISPATCH_TIME_NOW
DISPATCH_TIME_FOREVER = _DISPATCH_TIME_FOREVER

# Queue priority constants
DEF _DISPATCH_QUEUE_PRIORITY_HIGH = 2
DEF _DISPATCH_QUEUE_PRIORITY_DEFAULT = 0
DEF _DISPATCH_QUEUE_PRIORITY_LOW = -2
DEF _DISPATCH_QUEUE_PRIORITY_BACKGROUND = -32768  # INT16_MIN

QUEUE_PRIORITY_HIGH = _DISPATCH_QUEUE_PRIORITY_HIGH
QUEUE_PRIORITY_DEFAULT = _DISPATCH_QUEUE_PRIORITY_DEFAULT
QUEUE_PRIORITY_LOW = _DISPATCH_QUEUE_PRIORITY_LOW
QUEUE_PRIORITY_BACKGROUND = _DISPATCH_QUEUE_PRIORITY_BACKGROUND

# QOS class constants (from sys/qos.h)
DEF _QOS_CLASS_USER_INTERACTIVE = 0x21
DEF _QOS_CLASS_USER_INITIATED = 0x19
DEF _QOS_CLASS_DEFAULT = 0x15
DEF _QOS_CLASS_UTILITY = 0x11
DEF _QOS_CLASS_BACKGROUND = 0x09
DEF _QOS_CLASS_UNSPECIFIED = 0x00

QOS_CLASS_USER_INTERACTIVE = _QOS_CLASS_USER_INTERACTIVE
QOS_CLASS_USER_INITIATED = _QOS_CLASS_USER_INITIATED
QOS_CLASS_DEFAULT = _QOS_CLASS_DEFAULT
QOS_CLASS_UTILITY = _QOS_CLASS_UTILITY
QOS_CLASS_BACKGROUND = _QOS_CLASS_BACKGROUND
QOS_CLASS_UNSPECIFIED = _QOS_CLASS_UNSPECIFIED

# Process event flags (from dispatch/source.h)
DEF _DISPATCH_PROC_EXIT = 0x80000000
DEF _DISPATCH_PROC_FORK = 0x40000000
DEF _DISPATCH_PROC_EXEC = 0x20000000
DEF _DISPATCH_PROC_SIGNAL = 0x08000000

PROC_EXIT = _DISPATCH_PROC_EXIT
PROC_FORK = _DISPATCH_PROC_FORK
PROC_EXEC = _DISPATCH_PROC_EXEC
PROC_SIGNAL = _DISPATCH_PROC_SIGNAL


cdef extern from "time.h" nogil:
    ctypedef long time_t
    struct timespec:
        time_t tv_sec
        long tv_nsec


cdef extern from "dispatch/dispatch.h" nogil:
    # Opaque types
    ctypedef struct dispatch_queue_s:
        pass
    ctypedef dispatch_queue_s* dispatch_queue_t

    ctypedef struct dispatch_group_s:
        pass
    ctypedef dispatch_group_s* dispatch_group_t

    ctypedef struct dispatch_semaphore_s:
        pass
    ctypedef dispatch_semaphore_s* dispatch_semaphore_t

    ctypedef struct dispatch_queue_attr_s:
        pass
    ctypedef dispatch_queue_attr_s* dispatch_queue_attr_t

    ctypedef struct dispatch_source_s:
        pass
    ctypedef dispatch_source_s* dispatch_source_t

    ctypedef struct dispatch_source_type_s:
        pass
    ctypedef const dispatch_source_type_s* dispatch_source_type_t

    # Time type
    ctypedef uint64_t dispatch_time_t

    # Function pointer type
    ctypedef void (*dispatch_function_t)(void*)

    # Once predicate
    ctypedef intptr_t dispatch_once_t

    # Queue attribute constants
    dispatch_queue_attr_t _dispatch_queue_attr_concurrent "DISPATCH_GLOBAL_OBJECT(dispatch_queue_attr_t, _dispatch_queue_attr_concurrent)"

    # Source type constants
    dispatch_source_type_t _dispatch_source_type_timer "DISPATCH_SOURCE_TYPE_TIMER"
    dispatch_source_type_t _dispatch_source_type_signal "DISPATCH_SOURCE_TYPE_SIGNAL"
    dispatch_source_type_t _dispatch_source_type_read "DISPATCH_SOURCE_TYPE_READ"
    dispatch_source_type_t _dispatch_source_type_write "DISPATCH_SOURCE_TYPE_WRITE"
    dispatch_source_type_t _dispatch_source_type_proc "DISPATCH_SOURCE_TYPE_PROC"

    # Main queue
    dispatch_queue_t dispatch_get_main_queue()

    # Queue creation and management
    dispatch_queue_t dispatch_queue_create(const char* label, dispatch_queue_attr_t attr)
    dispatch_queue_t dispatch_get_global_queue(intptr_t identifier, uintptr_t flags)
    const char* dispatch_queue_get_label(dispatch_queue_t queue)

    # Reference counting
    void dispatch_retain(dispatch_queue_t obj)
    void dispatch_release(dispatch_queue_t obj)

    # Suspend/Resume
    void dispatch_suspend(dispatch_queue_t obj)
    void dispatch_resume(dispatch_queue_t obj)

    # Async/sync execution with function pointers
    void dispatch_async_f(dispatch_queue_t queue, void* context, dispatch_function_t work)
    void dispatch_sync_f(dispatch_queue_t queue, void* context, dispatch_function_t work)

    # Barrier operations
    void dispatch_barrier_async_f(dispatch_queue_t queue, void* context, dispatch_function_t work)
    void dispatch_barrier_sync_f(dispatch_queue_t queue, void* context, dispatch_function_t work)

    # Apply (parallel for)
    void dispatch_apply_f(size_t iterations, dispatch_queue_t queue,
                          void* context, void (*work)(void*, size_t))

    # After (delayed execution)
    void dispatch_after_f(dispatch_time_t when, dispatch_queue_t queue,
                          void* context, dispatch_function_t work)

    # Groups
    dispatch_group_t dispatch_group_create()
    void dispatch_group_async_f(dispatch_group_t group, dispatch_queue_t queue,
                                void* context, dispatch_function_t work)
    intptr_t dispatch_group_wait(dispatch_group_t group, dispatch_time_t timeout)
    void dispatch_group_notify_f(dispatch_group_t group, dispatch_queue_t queue,
                                 void* context, dispatch_function_t work)
    void dispatch_group_enter(dispatch_group_t group)
    void dispatch_group_leave(dispatch_group_t group)

    # Semaphores
    dispatch_semaphore_t dispatch_semaphore_create(intptr_t value)
    intptr_t dispatch_semaphore_wait(dispatch_semaphore_t dsema, dispatch_time_t timeout)
    intptr_t dispatch_semaphore_signal(dispatch_semaphore_t dsema)

    # Once
    void dispatch_once_f(dispatch_once_t* predicate, void* context, dispatch_function_t function)

    # Time functions
    dispatch_time_t dispatch_time(dispatch_time_t when, int64_t delta)
    dispatch_time_t dispatch_walltime(const timespec* when, int64_t delta)

    # Source functions
    dispatch_source_t dispatch_source_create(dispatch_source_type_t type,
                                             uintptr_t handle,
                                             uintptr_t mask,
                                             dispatch_queue_t queue)
    void dispatch_source_set_event_handler_f(dispatch_source_t source,
                                             dispatch_function_t handler)
    void dispatch_source_set_cancel_handler_f(dispatch_source_t source,
                                              dispatch_function_t handler)
    void dispatch_source_cancel(dispatch_source_t source)
    intptr_t dispatch_source_testcancel(dispatch_source_t source)
    void dispatch_source_set_timer(dispatch_source_t source,
                                   dispatch_time_t start,
                                   uint64_t interval,
                                   uint64_t leeway)
    uintptr_t dispatch_source_get_data(dispatch_source_t source)
    uintptr_t dispatch_source_get_handle(dispatch_source_t source)
    uintptr_t dispatch_source_get_mask(dispatch_source_t source)
    void dispatch_set_context(dispatch_source_t obj, void* context)

    # Queue hierarchy
    void dispatch_set_target_queue(dispatch_queue_t object, dispatch_queue_t queue)

    # QOS attributes
    dispatch_queue_attr_t dispatch_queue_attr_make_with_qos_class(
        dispatch_queue_attr_t attr, unsigned int qos_class, int relative_priority)

    # Inactive queues
    dispatch_queue_attr_t dispatch_queue_attr_make_initially_inactive(
        dispatch_queue_attr_t attr)
    void dispatch_activate(dispatch_queue_t object)

    # Queue-specific data
    ctypedef const void* dispatch_queue_key_t
    void dispatch_queue_set_specific(dispatch_queue_t queue, const void* key,
                                     void* context, dispatch_function_t destructor)
    void* dispatch_queue_get_specific(dispatch_queue_t queue, const void* key)
    void* dispatch_get_specific(const void* key)

    # Dispatch I/O types
    ctypedef struct dispatch_io_s:
        pass
    ctypedef dispatch_io_s* dispatch_io_t

    ctypedef struct dispatch_data_s:
        pass
    ctypedef dispatch_data_s* dispatch_data_t

    # Dispatch data empty constant
    dispatch_data_t _dispatch_data_empty "DISPATCH_DATA_DESTRUCTOR_DEFAULT"

    # Dispatch I/O type constants
    unsigned int DISPATCH_IO_STREAM
    unsigned int DISPATCH_IO_RANDOM

    # Dispatch I/O close flags
    unsigned int DISPATCH_IO_STOP

    # Dispatch I/O functions (block parameters declared as void* for ObjC blocks)
    dispatch_io_t dispatch_io_create(unsigned int type, int fd,
                                     dispatch_queue_t queue,
                                     void* cleanup_handler)
    dispatch_io_t dispatch_io_create_with_path(unsigned int type, const char* path,
                                               int oflag, unsigned short mode,
                                               dispatch_queue_t queue,
                                               void* cleanup_handler)
    void dispatch_io_read(dispatch_io_t channel, off_t offset, size_t length,
                          dispatch_queue_t queue,
                          void* handler)
    void dispatch_io_write(dispatch_io_t channel, off_t offset, dispatch_data_t data,
                           dispatch_queue_t queue,
                           void* handler)
    void dispatch_io_close(dispatch_io_t channel, unsigned int flags)
    void dispatch_io_set_high_water(dispatch_io_t channel, size_t high_water)
    void dispatch_io_set_low_water(dispatch_io_t channel, size_t low_water)
    void dispatch_io_set_interval(dispatch_io_t channel, uint64_t interval,
                                  unsigned int flags)
    void dispatch_io_barrier(dispatch_io_t channel, void* barrier)

    # Dispatch Data functions
    dispatch_data_t dispatch_data_create(const void* buffer, size_t size,
                                         dispatch_queue_t queue,
                                         void (*destructor)())
    size_t dispatch_data_get_size(dispatch_data_t data)
    dispatch_data_t dispatch_data_create_concat(dispatch_data_t data1,
                                                dispatch_data_t data2)
    dispatch_data_t dispatch_data_create_subrange(dispatch_data_t data,
                                                  size_t offset, size_t length)
    dispatch_data_t dispatch_data_create_map(dispatch_data_t data,
                                             const void** buffer_ptr,
                                             size_t* size_ptr)
    bint dispatch_data_apply(dispatch_data_t data,
                             bint (*applier)(dispatch_data_t region,
                                            size_t offset,
                                            const void* buffer,
                                            size_t size))

    # Simple async I/O
    void dispatch_read(int fd, size_t length, dispatch_queue_t queue,
                       void (*handler)(dispatch_data_t data, int error))
    void dispatch_write(int fd, dispatch_data_t data, dispatch_queue_t queue,
                        void (*handler)(dispatch_data_t data, int error))

    # Workloop
    ctypedef struct dispatch_workloop_s:
        pass
    ctypedef dispatch_workloop_s* dispatch_workloop_t

    dispatch_workloop_t dispatch_workloop_create(const char* label)
    dispatch_workloop_t dispatch_workloop_create_inactive(const char* label)

    # Autorelease frequency constants
    unsigned int DISPATCH_AUTORELEASE_FREQUENCY_INHERIT
    unsigned int DISPATCH_AUTORELEASE_FREQUENCY_WORK_ITEM
    unsigned int DISPATCH_AUTORELEASE_FREQUENCY_NEVER

    void dispatch_workloop_set_autorelease_frequency(
        dispatch_workloop_t workloop, unsigned int frequency)

    # Object context (generic for all dispatch objects)
    void* dispatch_get_context(dispatch_queue_t obj)
    void dispatch_set_finalizer_f(dispatch_queue_t obj, dispatch_function_t finalizer)

    # Dispatch data copy_region
    dispatch_data_t dispatch_data_copy_region(dispatch_data_t data,
                                              size_t location,
                                              size_t* offset_ptr)


# Inline Objective-C code for block support
# This enables dispatch_io functions which require ObjC blocks
cdef extern from *:
    """
    #import <dispatch/dispatch.h>
    #import <Block.h>

    // Forward declaration of Python callback invoker (defined in Cython)
    // Note: Cython's bint becomes int in C, not _Bool
    extern void _cygcd_invoke_io_callback(unsigned long cb_id, int done,
                                          dispatch_data_t data, int error);
    extern void _cygcd_invoke_cleanup_callback(unsigned long cb_id, int error);
    extern void _cygcd_invoke_barrier_callback(unsigned long cb_id);

    // Create an I/O handler block that calls back to Python
    static inline void* _cygcd_create_io_block(unsigned long cb_id) {
        dispatch_io_handler_t block = ^(bool done, dispatch_data_t data, int error) {
            _cygcd_invoke_io_callback(cb_id, done, data, error);
        };
        return Block_copy(block);
    }

    // Create a cleanup handler block
    static inline void* _cygcd_create_cleanup_block(unsigned long cb_id) {
        dispatch_io_handler_t block = ^(bool done, dispatch_data_t data, int error) {
            // Cleanup handler signature differs - it receives (int error) only
            // But dispatch_io_create expects the same block type
            // Actually, cleanup_handler is void(^)(int error)
        };
        return NULL;  // Will implement properly below
    }

    // Proper cleanup block type
    typedef void (^cleanup_block_t)(int);
    static inline void* _cygcd_create_cleanup_block_v2(unsigned long cb_id) {
        cleanup_block_t block = ^(int error) {
            _cygcd_invoke_cleanup_callback(cb_id, error);
        };
        return Block_copy(block);
    }

    // Create a barrier block
    typedef void (^barrier_block_t)(void);
    static inline void* _cygcd_create_barrier_block(unsigned long cb_id) {
        barrier_block_t block = ^{
            _cygcd_invoke_barrier_callback(cb_id);
        };
        return Block_copy(block);
    }

    // Release a block
    static inline void _cygcd_release_block(void* block) {
        if (block != NULL) {
            Block_release(block);
        }
    }
    """
    void* _cygcd_create_io_block(unsigned long cb_id) nogil
    void* _cygcd_create_cleanup_block_v2(unsigned long cb_id) nogil
    void* _cygcd_create_barrier_block(unsigned long cb_id) nogil
    void _cygcd_release_block(void* block) nogil


# Storage for I/O channel callbacks (prevent garbage collection)
cdef dict _iochannel_callbacks = {}
cdef unsigned long _iochannel_callback_counter = 0


cdef unsigned long _register_io_callback(object callback):
    """Register a callback and return its ID."""
    global _iochannel_callback_counter
    cdef unsigned long cb_id = _iochannel_callback_counter
    _iochannel_callback_counter += 1
    Py_INCREF(callback)
    _iochannel_callbacks[cb_id] = callback
    return cb_id


cdef object _get_io_callback(unsigned long cb_id):
    """Get a callback by ID (does not remove it)."""
    return _iochannel_callbacks.get(cb_id)


cdef void _unregister_io_callback(unsigned long cb_id):
    """Unregister and decref a callback."""
    cdef object callback = _iochannel_callbacks.pop(cb_id, None)
    if callback is not None:
        Py_DECREF(callback)


# C-callable functions that the blocks invoke
cdef public void _cygcd_invoke_io_callback(unsigned long cb_id, bint done,
                                           dispatch_data_t data, int error) noexcept with gil:
    """Called from ObjC block to invoke Python I/O callback."""
    cdef object callback = _get_io_callback(cb_id)
    if callback is None:
        return

    # Convert dispatch_data to bytes
    cdef bytes py_data = b""
    cdef const void* buffer = NULL
    cdef size_t size = 0
    cdef dispatch_data_t mapped = NULL

    if data != NULL:
        with nogil:
            mapped = dispatch_data_create_map(data, &buffer, &size)
        if mapped != NULL and buffer != NULL and size > 0:
            py_data = (<const char*>buffer)[:size]
        if mapped != NULL:
            with nogil:
                dispatch_release(<dispatch_queue_t>mapped)

    try:
        callback(done, py_data, error)
    except BaseException:
        PyErr_Print()

    # If done, unregister the callback
    if done:
        _unregister_io_callback(cb_id)


cdef public void _cygcd_invoke_cleanup_callback(unsigned long cb_id, int error) noexcept with gil:
    """Called from ObjC block to invoke Python cleanup callback."""
    cdef object callback = _get_io_callback(cb_id)
    if callback is None:
        return

    try:
        callback(error)
    except BaseException:
        PyErr_Print()

    # Cleanup is always final
    _unregister_io_callback(cb_id)


cdef public void _cygcd_invoke_barrier_callback(unsigned long cb_id) noexcept with gil:
    """Called from ObjC block to invoke Python barrier callback."""
    cdef object callback = _get_io_callback(cb_id)
    if callback is None:
        return

    try:
        callback()
    except BaseException:
        PyErr_Print()

    # Barrier is always final
    _unregister_io_callback(cb_id)


# Autorelease frequency constants for Workloop
AUTORELEASE_FREQUENCY_INHERIT = 0      # DISPATCH_AUTORELEASE_FREQUENCY_INHERIT
AUTORELEASE_FREQUENCY_WORK_ITEM = 1    # DISPATCH_AUTORELEASE_FREQUENCY_WORK_ITEM
AUTORELEASE_FREQUENCY_NEVER = 2        # DISPATCH_AUTORELEASE_FREQUENCY_NEVER


# Context management for dispatch objects
# Maps object id -> (context_value, finalizer)
cdef dict _object_contexts = {}
cdef unsigned long _context_counter = 0


cdef unsigned long _register_context(object value, object finalizer):
    """Register a context and return its ID."""
    global _context_counter
    cdef unsigned long ctx_id = _context_counter
    _context_counter += 1
    if value is not None:
        Py_INCREF(value)
    if finalizer is not None:
        Py_INCREF(finalizer)
    _object_contexts[ctx_id] = (value, finalizer)
    return ctx_id


cdef object _get_context_value(unsigned long ctx_id):
    """Get context value by ID."""
    entry = _object_contexts.get(ctx_id)
    if entry is not None:
        return entry[0]
    return None


cdef void _unregister_context(unsigned long ctx_id):
    """Unregister context and call finalizer if set."""
    entry = _object_contexts.pop(ctx_id, None)
    if entry is not None:
        value, finalizer = entry
        if finalizer is not None:
            try:
                finalizer()
            except BaseException:
                PyErr_Print()
            Py_DECREF(finalizer)
        if value is not None:
            Py_DECREF(value)


# Trampoline for context finalizer
cdef void _python_context_finalizer(void* context) noexcept with gil:
    """Trampoline for dispatch object finalizer."""
    if context == NULL:
        return
    cdef unsigned long ctx_id = <unsigned long><uintptr_t>context
    _unregister_context(ctx_id)


# Queue-specific data storage
# Maps (queue_id, key) -> value
cdef dict _queue_specific_data = {}
cdef dict _queue_specific_keys = {}  # key_id -> key object (to prevent GC)
cdef unsigned long _specific_key_counter = 0


cdef unsigned long _create_specific_key():
    """Create a new queue-specific key."""
    global _specific_key_counter
    cdef unsigned long key_id = _specific_key_counter
    _specific_key_counter += 1
    return key_id


cdef void _specific_destructor(void* context) noexcept with gil:
    """Destructor for queue-specific data."""
    if context == NULL:
        return
    # Context is the Python object itself
    cdef object value = <object>context
    Py_DECREF(value)


# Trampoline function that acquires GIL and calls Python callable
cdef void _python_callback(void* context) noexcept with gil:
    """Trampoline function to call Python callables from GCD."""
    cdef object func
    if context == NULL:
        return
    func = <object>context
    try:
        func()
    except BaseException:
        PyErr_Print()
    finally:
        Py_DECREF(func)


# Trampoline for dispatch_apply with iteration index
cdef void _python_apply_callback(void* context, size_t iteration) noexcept with gil:
    """Trampoline function for dispatch_apply that passes iteration index."""
    cdef object func
    if context == NULL:
        return
    func = <object>context
    try:
        func(iteration)
    except BaseException:
        PyErr_Print()


# Trampoline for timer events - does NOT decref since timer fires repeatedly
cdef void _python_timer_callback(void* context) noexcept with gil:
    """Trampoline function for timer events."""
    cdef object func
    if context == NULL:
        return
    func = <object>context
    try:
        func()
    except BaseException:
        PyErr_Print()


# Trampoline for timer cancel handler - decrefs the callback
cdef void _python_timer_cancel_callback(void* context) noexcept with gil:
    """Trampoline function for timer cancel - releases the callback reference."""
    cdef object func
    if context == NULL:
        return
    func = <object>context
    Py_DECREF(func)


cdef class Queue:
    """
    Dispatch queue wrapper.

    Queues can be serial (execute one task at a time in FIFO order) or
    concurrent (execute multiple tasks simultaneously).
    """
    cdef dispatch_queue_t _queue
    cdef bint _owned
    cdef bint _inactive
    cdef bytes _label_bytes
    cdef unsigned long _context_id
    cdef bint _has_context

    def __cinit__(self):
        self._queue = NULL
        self._owned = False
        self._inactive = False
        self._context_id = 0
        self._has_context = False

    def __init__(self, str label=None, bint concurrent=False,
                 int qos=_QOS_CLASS_UNSPECIFIED, int relative_priority=0,
                 target=None, bint inactive=False):
        """
        Create a new dispatch queue.

        Args:
            label: Optional string label for debugging.
            concurrent: If True, create a concurrent queue. Default is serial.
            qos: Quality of Service class (QOS_CLASS_* constants). Default is unspecified.
            relative_priority: Priority offset within QOS class (-15 to 0). Default is 0.
            target: Optional target queue for queue hierarchy. Tasks submitted to this
                    queue will ultimately execute on the target queue.
            inactive: If True, create queue in inactive state. Must call activate()
                      before the queue will process tasks. Default is False.
        """
        cdef dispatch_queue_attr_t attr
        cdef const char* c_label = NULL

        if label is not None:
            self._label_bytes = label.encode('utf-8')
            c_label = self._label_bytes

        if concurrent:
            attr = _dispatch_queue_attr_concurrent
        else:
            attr = NULL  # DISPATCH_QUEUE_SERIAL

        # Apply QOS if specified
        if qos != _QOS_CLASS_UNSPECIFIED:
            with nogil:
                attr = dispatch_queue_attr_make_with_qos_class(
                    attr, <unsigned int>qos, relative_priority)

        # Make inactive if specified
        if inactive:
            with nogil:
                attr = dispatch_queue_attr_make_initially_inactive(attr)
            self._inactive = True

        with nogil:
            self._queue = dispatch_queue_create(c_label, attr)
        self._owned = True

        # Set target queue if specified
        if target is not None:
            self.set_target_queue(target)

    def __dealloc__(self):
        if self._queue != NULL and self._owned:
            # Must activate inactive queues before releasing
            # otherwise dispatch_release will block forever
            if self._inactive:
                dispatch_activate(self._queue)
            dispatch_release(self._queue)
            self._queue = NULL

    @staticmethod
    def global_queue(int priority=_DISPATCH_QUEUE_PRIORITY_DEFAULT):
        """
        Get a global concurrent queue with the specified priority.

        Args:
            priority: Queue priority (QUEUE_PRIORITY_* or QOS_CLASS_* constants).

        Returns:
            A Queue instance wrapping the global queue.
        """
        cdef Queue q = Queue.__new__(Queue)
        with nogil:
            q._queue = dispatch_get_global_queue(priority, 0)
        q._owned = False  # Global queues are not owned
        return q

    @staticmethod
    def main_queue():
        """
        Get the main queue.

        The main queue is a serial queue associated with the main thread.
        Tasks submitted to the main queue execute on the main thread.

        Note: In a Python application without a running CFRunLoop or NSRunLoop,
        the main queue will not process tasks automatically. Use this primarily
        when integrating with macOS GUI frameworks.

        Returns:
            A Queue instance wrapping the main queue.
        """
        cdef Queue q = Queue.__new__(Queue)
        q._queue = dispatch_get_main_queue()
        q._owned = False  # Main queue is not owned
        return q

    @property
    def label(self):
        """Get the queue's label."""
        cdef const char* c_label
        with nogil:
            c_label = dispatch_queue_get_label(self._queue)
        if c_label == NULL:
            return None
        return c_label.decode('utf-8')

    def set_target_queue(self, Queue target):
        """
        Set the target queue for this queue.

        Tasks submitted to this queue will ultimately execute on the target queue.
        This creates a queue hierarchy that can be used for priority management.

        Note: The target queue should be set before any tasks are submitted.
        Changing the target queue after tasks have been submitted may result
        in undefined behavior.

        Args:
            target: The target queue, or None to reset to default.
        """
        cdef dispatch_queue_t target_q = NULL
        if target is not None:
            target_q = target._queue
        with nogil:
            dispatch_set_target_queue(self._queue, target_q)

    def run_async(self, func):
        """
        Submit a callable for asynchronous execution.

        The callable will be executed on this queue at some point in the future.
        This method returns immediately.

        Args:
            func: A callable taking no arguments.
        """
        if not callable(func):
            raise TypeError("func must be callable")
        Py_INCREF(func)
        cdef PyObject* ctx = <PyObject*>func
        with nogil:
            dispatch_async_f(self._queue, <void*>ctx, _python_callback)

    def run_sync(self, func):
        """
        Submit a callable for synchronous execution.

        This method blocks until the callable has completed execution.

        Warning: Do not call run_sync() on a serial queue from within a task
        already running on that queue - this will deadlock.

        Args:
            func: A callable taking no arguments.
        """
        if not callable(func):
            raise TypeError("func must be callable")
        Py_INCREF(func)
        cdef PyObject* ctx = <PyObject*>func
        with nogil:
            dispatch_sync_f(self._queue, <void*>ctx, _python_callback)

    def barrier_async(self, func):
        """
        Submit a barrier callable for asynchronous execution.

        On a concurrent queue, barrier tasks wait for all previously submitted
        tasks to complete, then execute exclusively (no other tasks run
        concurrently), then allow subsequent tasks to proceed.

        On a serial queue, this behaves identically to async_().

        Args:
            func: A callable taking no arguments.
        """
        if not callable(func):
            raise TypeError("func must be callable")
        Py_INCREF(func)
        cdef PyObject* ctx = <PyObject*>func
        with nogil:
            dispatch_barrier_async_f(self._queue, <void*>ctx, _python_callback)

    def barrier_sync(self, func):
        """
        Submit a barrier callable for synchronous execution.

        Combines the semantics of barrier_async() and sync().

        Args:
            func: A callable taking no arguments.
        """
        if not callable(func):
            raise TypeError("func must be callable")
        Py_INCREF(func)
        cdef PyObject* ctx = <PyObject*>func
        with nogil:
            dispatch_barrier_sync_f(self._queue, <void*>ctx, _python_callback)

    def after(self, double delay_seconds, func):
        """
        Schedule a callable for execution after a delay.

        Args:
            delay_seconds: Delay in seconds before execution.
            func: A callable taking no arguments.
        """
        if not callable(func):
            raise TypeError("func must be callable")
        cdef int64_t delta_ns = <int64_t>(delay_seconds * NSEC_PER_SEC)
        cdef dispatch_time_t when
        with nogil:
            when = dispatch_time(_DISPATCH_TIME_NOW, delta_ns)
        Py_INCREF(func)
        cdef PyObject* ctx = <PyObject*>func
        with nogil:
            dispatch_after_f(when, self._queue, <void*>ctx, _python_callback)

    def suspend(self):
        """
        Suspend the queue.

        Suspending a queue prevents it from executing any tasks.
        Calls to suspend must be balanced with calls to resume.

        Note: Suspending a queue does not interrupt a task that is
        currently executing.
        """
        cdef dispatch_queue_t q = self._queue
        with nogil:
            dispatch_suspend(q)

    def resume(self):
        """
        Resume the queue.

        Resumes a suspended queue, allowing it to execute tasks again.
        Calls to resume must balance previous calls to suspend.
        """
        cdef dispatch_queue_t q = self._queue
        with nogil:
            dispatch_resume(q)

    def activate(self):
        """
        Activate an inactive queue.

        Queues created with inactive=True must be activated before they will
        process any tasks. Once activated, a queue cannot be made inactive again.

        Raises:
            RuntimeError: If the queue was not created as inactive.
        """
        if not self._inactive:
            raise RuntimeError("Queue was not created as inactive")
        cdef dispatch_queue_t q = self._queue
        with nogil:
            dispatch_activate(q)
        self._inactive = False

    @property
    def is_inactive(self):
        """Check if the queue is currently inactive."""
        return self._inactive

    def set_context(self, value, finalizer=None):
        """
        Attach arbitrary context data to this queue.

        The context data can be retrieved later with get_context().
        An optional finalizer callable is invoked when the queue is deallocated.

        Args:
            value: Any Python object to attach to the queue.
            finalizer: Optional callable with no arguments, called when
                       the queue is deallocated or context is replaced.

        Raises:
            TypeError: If finalizer is provided but not callable.
        """
        if finalizer is not None and not callable(finalizer):
            raise TypeError("finalizer must be callable")

        # Clear existing context if any
        if self._has_context:
            _unregister_context(self._context_id)

        # Register new context
        self._context_id = _register_context(value, finalizer)
        self._has_context = True

        # Set GCD context to our context ID (for finalizer dispatch)
        cdef dispatch_queue_t q = self._queue
        cdef void* ctx_ptr = <void*><uintptr_t>self._context_id
        with nogil:
            dispatch_set_context(<dispatch_source_t>q, ctx_ptr)
            dispatch_set_finalizer_f(q, _python_context_finalizer)

    def get_context(self):
        """
        Get the context data attached to this queue.

        Returns:
            The context value set with set_context(), or None if not set.
        """
        if not self._has_context:
            return None
        return _get_context_value(self._context_id)

    def set_specific(self, key, value):
        """
        Set queue-specific data for a key.

        This data is associated with this specific queue and can be retrieved
        from any code executing on this queue using get_specific().

        Args:
            key: A hashable key to identify the data.
            value: Any Python object to store (or None to remove).
        """
        # Use the key's id as the dispatch key
        cdef uintptr_t dispatch_key = <uintptr_t>id(key)
        cdef dispatch_queue_t q = self._queue
        cdef PyObject* ctx

        # Store key to prevent GC
        _queue_specific_keys[id(key)] = key

        if value is None:
            # Remove the specific data
            with nogil:
                dispatch_queue_set_specific(q, <const void*>dispatch_key, NULL, NULL)
            # Clean up our storage
            storage_key = (id(self), id(key))
            _queue_specific_data.pop(storage_key, None)
        else:
            # Store in our dict for reference counting
            storage_key = (id(self), id(key))
            old_value = _queue_specific_data.get(storage_key)
            _queue_specific_data[storage_key] = value

            Py_INCREF(value)
            ctx = <PyObject*>value
            with nogil:
                dispatch_queue_set_specific(q, <const void*>dispatch_key,
                                           <void*>ctx, _specific_destructor)

    def get_specific(self, key):
        """
        Get queue-specific data for a key from this queue.

        Args:
            key: The key used in set_specific().

        Returns:
            The stored value, or None if not set.
        """
        cdef uintptr_t dispatch_key = <uintptr_t>id(key)
        cdef dispatch_queue_t q = self._queue
        cdef void* result
        with nogil:
            result = dispatch_queue_get_specific(q, <const void*>dispatch_key)
        if result == NULL:
            return None
        return <object>result


def get_specific(key):
    """
    Get queue-specific data for a key from the current queue.

    This function retrieves data set with Queue.set_specific() from
    code running on that queue.

    Args:
        key: The key used in set_specific().

    Returns:
        The stored value, or None if not set or not running on a queue.
    """
    cdef uintptr_t dispatch_key = <uintptr_t>id(key)
    cdef void* result
    with nogil:
        result = dispatch_get_specific(<const void*>dispatch_key)
    if result == NULL:
        return None
    return <object>result


def apply(size_t iterations, func, Queue queue=None):
    """
    Execute a callable multiple times in parallel.

    The callable is invoked `iterations` times, potentially concurrently.
    Each invocation receives its iteration index (0 to iterations-1).
    This function blocks until all iterations complete.

    Args:
        iterations: Number of times to invoke the callable.
        func: A callable taking one argument (the iteration index).
        queue: Optional queue to use. If None, uses an appropriate global queue.
    """
    if not callable(func):
        raise TypeError("func must be callable")

    cdef dispatch_queue_t q
    if queue is not None:
        q = queue._queue
    else:
        q = NULL  # DISPATCH_APPLY_AUTO

    # For apply, we don't need to manage reference counting per-iteration
    # because dispatch_apply_f is synchronous
    cdef PyObject* ctx = <PyObject*>func
    with nogil:
        dispatch_apply_f(iterations, q, <void*>ctx, _python_apply_callback)


cdef class Group:
    """
    Dispatch group for tracking completion of multiple tasks.

    Groups allow you to aggregate multiple tasks and wait for all of them
    to complete, or be notified when they complete.
    """
    cdef dispatch_group_t _group

    def __cinit__(self):
        self._group = NULL

    def __init__(self):
        """Create a new dispatch group."""
        with nogil:
            self._group = dispatch_group_create()

    def __dealloc__(self):
        if self._group != NULL:
            dispatch_release(<dispatch_queue_t>self._group)
            self._group = NULL

    def run_async(self, Queue queue, func):
        """
        Submit a callable to a queue and associate it with this group.

        Args:
            queue: The queue to submit to.
            func: A callable taking no arguments.
        """
        if not callable(func):
            raise TypeError("func must be callable")
        Py_INCREF(func)
        cdef PyObject* ctx = <PyObject*>func
        cdef dispatch_queue_t q = queue._queue
        cdef dispatch_group_t g = self._group
        with nogil:
            dispatch_group_async_f(g, q, <void*>ctx, _python_callback)

    def wait(self, double timeout_seconds=-1.0):
        """
        Wait for all tasks in the group to complete.

        Args:
            timeout_seconds: Maximum time to wait. Use -1 for infinite wait.

        Returns:
            True if all tasks completed, False if timeout occurred.
        """
        cdef dispatch_time_t timeout
        cdef intptr_t result
        cdef int64_t delta_ns

        if timeout_seconds < 0:
            timeout = _DISPATCH_TIME_FOREVER
        else:
            delta_ns = <int64_t>(timeout_seconds * NSEC_PER_SEC)
            with nogil:
                timeout = dispatch_time(_DISPATCH_TIME_NOW, delta_ns)

        cdef dispatch_group_t g = self._group
        with nogil:
            result = dispatch_group_wait(g, timeout)
        return result == 0

    def notify(self, Queue queue, func):
        """
        Schedule a callable to run when all current tasks in the group complete.

        Args:
            queue: The queue to submit the notification callable to.
            func: A callable taking no arguments.
        """
        if not callable(func):
            raise TypeError("func must be callable")
        Py_INCREF(func)
        cdef PyObject* ctx = <PyObject*>func
        cdef dispatch_queue_t q = queue._queue
        cdef dispatch_group_t g = self._group
        with nogil:
            dispatch_group_notify_f(g, q, <void*>ctx, _python_callback)

    def enter(self):
        """
        Manually increment the group's task count.

        Must be balanced with a call to leave().
        """
        cdef dispatch_group_t g = self._group
        with nogil:
            dispatch_group_enter(g)

    def leave(self):
        """
        Manually decrement the group's task count.

        Must balance a previous call to enter().
        """
        cdef dispatch_group_t g = self._group
        with nogil:
            dispatch_group_leave(g)


cdef class Semaphore:
    """
    Counting semaphore for controlling access to resources.

    A semaphore with initial value N allows N concurrent accesses.
    """
    cdef dispatch_semaphore_t _semaphore

    def __cinit__(self):
        self._semaphore = NULL

    def __init__(self, intptr_t value=0):
        """
        Create a new semaphore.

        Args:
            value: Initial value. Use 0 for signaling, >0 for resource counting.
        """
        with nogil:
            self._semaphore = dispatch_semaphore_create(value)

    def __dealloc__(self):
        if self._semaphore != NULL:
            dispatch_release(<dispatch_queue_t>self._semaphore)
            self._semaphore = NULL

    def wait(self, double timeout_seconds=-1.0):
        """
        Decrement the semaphore, blocking if necessary.

        If the semaphore value is greater than zero, decrements it and returns
        immediately. Otherwise, blocks until another thread signals.

        Args:
            timeout_seconds: Maximum time to wait. Use -1 for infinite wait.

        Returns:
            True if the semaphore was successfully decremented,
            False if timeout occurred.
        """
        cdef dispatch_time_t timeout
        cdef intptr_t result
        cdef int64_t delta_ns

        if timeout_seconds < 0:
            timeout = _DISPATCH_TIME_FOREVER
        else:
            delta_ns = <int64_t>(timeout_seconds * NSEC_PER_SEC)
            with nogil:
                timeout = dispatch_time(_DISPATCH_TIME_NOW, delta_ns)

        cdef dispatch_semaphore_t s = self._semaphore
        with nogil:
            result = dispatch_semaphore_wait(s, timeout)
        return result == 0

    def signal(self):
        """
        Increment the semaphore, potentially waking a waiting thread.

        Returns:
            True if a thread was woken, False otherwise.
        """
        cdef intptr_t result
        cdef dispatch_semaphore_t s = self._semaphore
        with nogil:
            result = dispatch_semaphore_signal(s)
        return result != 0


cdef class Once:
    """
    Execute a callable exactly once, thread-safely.

    Multiple threads can call the once instance simultaneously;
    only one will execute the callable, and all will wait for completion.
    """
    cdef dispatch_once_t _predicate

    def __cinit__(self):
        self._predicate = 0

    def __call__(self, func):
        """
        Execute the callable if not already executed.

        Args:
            func: A callable taking no arguments. Will only be called once.
        """
        if not callable(func):
            raise TypeError("func must be callable")

        # For once, we need special handling because the function should only
        # be called once, but we always increment the reference
        # We'll use a simple check - if predicate is already set, don't call
        if self._predicate != 0:
            return

        Py_INCREF(func)
        cdef PyObject* ctx = <PyObject*>func
        cdef dispatch_once_t* pred = &self._predicate
        with nogil:
            dispatch_once_f(pred, <void*>ctx, _python_callback)


def time_from_now(double seconds):
    """
    Create a dispatch time relative to now.

    Args:
        seconds: Number of seconds from now.

    Returns:
        A dispatch time value.
    """
    cdef int64_t delta_ns = <int64_t>(seconds * NSEC_PER_SEC)
    cdef dispatch_time_t result
    with nogil:
        result = dispatch_time(_DISPATCH_TIME_NOW, delta_ns)
    return result


def walltime(double timestamp=0.0, double delta_seconds=0.0):
    """
    Create a dispatch time based on wall clock time.

    Unlike time_from_now() which uses monotonic time, walltime uses
    the system clock and will adjust for clock changes (e.g., NTP, DST).

    Args:
        timestamp: Unix timestamp (seconds since epoch). If 0, uses current time.
        delta_seconds: Additional seconds to add to the timestamp.

    Returns:
        A dispatch time value based on wall clock time.
    """
    cdef timespec ts
    cdef timespec* ts_ptr
    cdef int64_t delta_ns = <int64_t>(delta_seconds * NSEC_PER_SEC)
    cdef dispatch_time_t result

    if timestamp == 0.0:
        ts_ptr = NULL  # Use current time
    else:
        ts.tv_sec = <time_t>timestamp
        ts.tv_nsec = <long>((timestamp - <double>ts.tv_sec) * NSEC_PER_SEC)
        ts_ptr = &ts

    with nogil:
        result = dispatch_walltime(ts_ptr, delta_ns)
    return result


cdef class Timer:
    """
    Dispatch timer source.

    Timers fire repeatedly at specified intervals, executing a handler
    on a target queue. Timers are created suspended and must be started
    with start().
    """
    cdef dispatch_source_t _source
    cdef object _handler
    cdef bint _started
    cdef bint _cancelled

    def __cinit__(self):
        self._source = NULL
        self._handler = None
        self._started = False
        self._cancelled = False

    def __init__(self, double interval, handler, Queue queue=None,
                 double start_delay=0.0, double leeway=0.0, bint repeating=True):
        """
        Create a new timer.

        Args:
            interval: Time between firings in seconds. For one-shot timers,
                      this is ignored (set repeating=False).
            handler: Callable to invoke when the timer fires. Takes no arguments.
            queue: Queue to execute handler on. If None, uses default global queue.
            start_delay: Initial delay before first firing (seconds). Default is 0.
            leeway: Allowed leeway for system power optimization (seconds).
                    Default is 0 (minimal leeway).
            repeating: If True (default), timer fires repeatedly. If False,
                       fires once then stops.
        """
        if not callable(handler):
            raise TypeError("handler must be callable")

        cdef dispatch_queue_t q
        if queue is not None:
            q = queue._queue
        else:
            q = NULL  # Default global queue

        # Create timer source
        with nogil:
            self._source = dispatch_source_create(
                _dispatch_source_type_timer, 0, 0, q)

        if self._source == NULL:
            raise RuntimeError("Failed to create timer source")

        # Configure timer
        cdef uint64_t interval_ns
        cdef uint64_t leeway_ns = <uint64_t>(leeway * NSEC_PER_SEC)
        cdef dispatch_time_t start_time
        cdef int64_t start_delta_ns = <int64_t>(start_delay * NSEC_PER_SEC)

        if repeating:
            interval_ns = <uint64_t>(interval * NSEC_PER_SEC)
        else:
            interval_ns = _DISPATCH_TIME_FOREVER  # One-shot

        with nogil:
            start_time = dispatch_time(_DISPATCH_TIME_NOW, start_delta_ns)
            dispatch_source_set_timer(self._source, start_time, interval_ns, leeway_ns)

        # Store handler and set up callbacks
        self._handler = handler
        Py_INCREF(handler)

        cdef PyObject* ctx = <PyObject*>handler
        with nogil:
            dispatch_set_context(<dispatch_source_t>self._source, <void*>ctx)
            dispatch_source_set_event_handler_f(self._source, _python_timer_callback)
            dispatch_source_set_cancel_handler_f(self._source, _python_timer_cancel_callback)

    def __dealloc__(self):
        if self._source != NULL:
            if not self._cancelled:
                # Must cancel before release
                dispatch_source_cancel(self._source)
            if not self._started:
                # Sources are created suspended, must resume before release
                dispatch_resume(<dispatch_queue_t>self._source)
            dispatch_release(<dispatch_queue_t>self._source)
            self._source = NULL

    def start(self):
        """
        Start the timer.

        The timer is created suspended and must be started to begin firing.
        """
        if self._started:
            return
        if self._cancelled:
            raise RuntimeError("Cannot start a cancelled timer")
        self._started = True
        with nogil:
            dispatch_resume(<dispatch_queue_t>self._source)

    def cancel(self):
        """
        Cancel the timer.

        After cancellation, the timer will not fire again.
        This is safe to call from any thread.
        """
        if self._cancelled:
            return
        self._cancelled = True
        with nogil:
            dispatch_source_cancel(self._source)

    @property
    def is_cancelled(self):
        """Check if the timer has been cancelled."""
        cdef intptr_t result
        with nogil:
            result = dispatch_source_testcancel(self._source)
        return result != 0

    def set_timer(self, double interval, double start_delay=0.0,
                  double leeway=0.0, bint repeating=True):
        """
        Reconfigure the timer's interval and start time.

        Can be called while the timer is running.

        Args:
            interval: Time between firings in seconds.
            start_delay: Delay before next firing (seconds).
            leeway: Allowed leeway for system power optimization (seconds).
            repeating: If True, timer fires repeatedly.
        """
        cdef uint64_t interval_ns
        cdef uint64_t leeway_ns = <uint64_t>(leeway * NSEC_PER_SEC)
        cdef dispatch_time_t start_time
        cdef int64_t start_delta_ns = <int64_t>(start_delay * NSEC_PER_SEC)

        if repeating:
            interval_ns = <uint64_t>(interval * NSEC_PER_SEC)
        else:
            interval_ns = _DISPATCH_TIME_FOREVER

        with nogil:
            start_time = dispatch_time(_DISPATCH_TIME_NOW, start_delta_ns)
            dispatch_source_set_timer(self._source, start_time, interval_ns, leeway_ns)


cdef class SignalSource:
    """
    Dispatch source for monitoring Unix signals.

    Allows handling signals asynchronously on a dispatch queue instead of
    using traditional signal handlers.

    Important: You must disable the default signal behavior for the signal
    you're monitoring (e.g., with signal.signal(sig, signal.SIG_IGN)).
    """
    cdef dispatch_source_t _source
    cdef object _handler
    cdef bint _started
    cdef bint _cancelled
    cdef int _signal

    def __cinit__(self):
        self._source = NULL
        self._handler = None
        self._started = False
        self._cancelled = False
        self._signal = 0

    def __init__(self, int signum, handler, Queue queue=None):
        """
        Create a new signal source.

        Args:
            signum: The Unix signal number to monitor (e.g., signal.SIGINT).
            handler: Callable to invoke when the signal is received.
                     Receives no arguments.
            queue: Queue to execute handler on. If None, uses default global queue.
        """
        if not callable(handler):
            raise TypeError("handler must be callable")

        self._signal = signum
        cdef dispatch_queue_t q
        if queue is not None:
            q = queue._queue
        else:
            q = NULL

        # Create signal source
        with nogil:
            self._source = dispatch_source_create(
                _dispatch_source_type_signal, <uintptr_t>signum, 0, q)

        if self._source == NULL:
            raise RuntimeError("Failed to create signal source")

        # Store handler and set up callbacks
        self._handler = handler
        Py_INCREF(handler)

        cdef PyObject* ctx = <PyObject*>handler
        with nogil:
            dispatch_set_context(<dispatch_source_t>self._source, <void*>ctx)
            dispatch_source_set_event_handler_f(self._source, _python_timer_callback)
            dispatch_source_set_cancel_handler_f(self._source, _python_timer_cancel_callback)

    def __dealloc__(self):
        if self._source != NULL:
            if not self._cancelled:
                dispatch_source_cancel(self._source)
            if not self._started:
                dispatch_resume(<dispatch_queue_t>self._source)
            dispatch_release(<dispatch_queue_t>self._source)
            self._source = NULL

    def start(self):
        """Start monitoring the signal."""
        if self._started:
            return
        if self._cancelled:
            raise RuntimeError("Cannot start a cancelled signal source")
        self._started = True
        with nogil:
            dispatch_resume(<dispatch_queue_t>self._source)

    def cancel(self):
        """Stop monitoring the signal."""
        if self._cancelled:
            return
        self._cancelled = True
        with nogil:
            dispatch_source_cancel(self._source)

    @property
    def is_cancelled(self):
        """Check if the source has been cancelled."""
        cdef intptr_t result
        with nogil:
            result = dispatch_source_testcancel(self._source)
        return result != 0

    @property
    def signal(self):
        """Get the signal number being monitored."""
        return self._signal

    @property
    def count(self):
        """
        Get the number of signals received since last handler invocation.

        This is useful for coalesced signals where multiple signals may have
        arrived before the handler ran.
        """
        cdef uintptr_t data
        with nogil:
            data = dispatch_source_get_data(self._source)
        return data


cdef class ReadSource:
    """
    Dispatch source for monitoring file descriptor readability.

    Fires when the file descriptor has data available to read.
    """
    cdef dispatch_source_t _source
    cdef object _handler
    cdef bint _started
    cdef bint _cancelled
    cdef int _fd

    def __cinit__(self):
        self._source = NULL
        self._handler = None
        self._started = False
        self._cancelled = False
        self._fd = -1

    def __init__(self, int fd, handler, Queue queue=None):
        """
        Create a new read source.

        Args:
            fd: The file descriptor to monitor.
            handler: Callable to invoke when data is available to read.
                     Receives no arguments.
            queue: Queue to execute handler on. If None, uses default global queue.
        """
        if not callable(handler):
            raise TypeError("handler must be callable")

        self._fd = fd
        cdef dispatch_queue_t q
        if queue is not None:
            q = queue._queue
        else:
            q = NULL

        # Create read source
        with nogil:
            self._source = dispatch_source_create(
                _dispatch_source_type_read, <uintptr_t>fd, 0, q)

        if self._source == NULL:
            raise RuntimeError("Failed to create read source")

        # Store handler and set up callbacks
        self._handler = handler
        Py_INCREF(handler)

        cdef PyObject* ctx = <PyObject*>handler
        with nogil:
            dispatch_set_context(<dispatch_source_t>self._source, <void*>ctx)
            dispatch_source_set_event_handler_f(self._source, _python_timer_callback)
            dispatch_source_set_cancel_handler_f(self._source, _python_timer_cancel_callback)

    def __dealloc__(self):
        if self._source != NULL:
            if not self._cancelled:
                dispatch_source_cancel(self._source)
            if not self._started:
                dispatch_resume(<dispatch_queue_t>self._source)
            dispatch_release(<dispatch_queue_t>self._source)
            self._source = NULL

    def start(self):
        """Start monitoring the file descriptor."""
        if self._started:
            return
        if self._cancelled:
            raise RuntimeError("Cannot start a cancelled read source")
        self._started = True
        with nogil:
            dispatch_resume(<dispatch_queue_t>self._source)

    def cancel(self):
        """Stop monitoring the file descriptor."""
        if self._cancelled:
            return
        self._cancelled = True
        with nogil:
            dispatch_source_cancel(self._source)

    @property
    def is_cancelled(self):
        """Check if the source has been cancelled."""
        cdef intptr_t result
        with nogil:
            result = dispatch_source_testcancel(self._source)
        return result != 0

    @property
    def fd(self):
        """Get the file descriptor being monitored."""
        return self._fd

    @property
    def bytes_available(self):
        """
        Get an estimate of the number of bytes available to read.

        This is an estimate and may not be exact.
        """
        cdef uintptr_t data
        with nogil:
            data = dispatch_source_get_data(self._source)
        return data


cdef class WriteSource:
    """
    Dispatch source for monitoring file descriptor writability.

    Fires when the file descriptor can accept data for writing.
    """
    cdef dispatch_source_t _source
    cdef object _handler
    cdef bint _started
    cdef bint _cancelled
    cdef int _fd

    def __cinit__(self):
        self._source = NULL
        self._handler = None
        self._started = False
        self._cancelled = False
        self._fd = -1

    def __init__(self, int fd, handler, Queue queue=None):
        """
        Create a new write source.

        Args:
            fd: The file descriptor to monitor.
            handler: Callable to invoke when writing is possible.
                     Receives no arguments.
            queue: Queue to execute handler on. If None, uses default global queue.
        """
        if not callable(handler):
            raise TypeError("handler must be callable")

        self._fd = fd
        cdef dispatch_queue_t q
        if queue is not None:
            q = queue._queue
        else:
            q = NULL

        # Create write source
        with nogil:
            self._source = dispatch_source_create(
                _dispatch_source_type_write, <uintptr_t>fd, 0, q)

        if self._source == NULL:
            raise RuntimeError("Failed to create write source")

        # Store handler and set up callbacks
        self._handler = handler
        Py_INCREF(handler)

        cdef PyObject* ctx = <PyObject*>handler
        with nogil:
            dispatch_set_context(<dispatch_source_t>self._source, <void*>ctx)
            dispatch_source_set_event_handler_f(self._source, _python_timer_callback)
            dispatch_source_set_cancel_handler_f(self._source, _python_timer_cancel_callback)

    def __dealloc__(self):
        if self._source != NULL:
            if not self._cancelled:
                dispatch_source_cancel(self._source)
            if not self._started:
                dispatch_resume(<dispatch_queue_t>self._source)
            dispatch_release(<dispatch_queue_t>self._source)
            self._source = NULL

    def start(self):
        """Start monitoring the file descriptor."""
        if self._started:
            return
        if self._cancelled:
            raise RuntimeError("Cannot start a cancelled write source")
        self._started = True
        with nogil:
            dispatch_resume(<dispatch_queue_t>self._source)

    def cancel(self):
        """Stop monitoring the file descriptor."""
        if self._cancelled:
            return
        self._cancelled = True
        with nogil:
            dispatch_source_cancel(self._source)

    @property
    def is_cancelled(self):
        """Check if the source has been cancelled."""
        cdef intptr_t result
        with nogil:
            result = dispatch_source_testcancel(self._source)
        return result != 0

    @property
    def fd(self):
        """Get the file descriptor being monitored."""
        return self._fd

    @property
    def buffer_space(self):
        """
        Get an estimate of the space available in the write buffer.

        This is an estimate and may not be exact.
        """
        cdef uintptr_t data
        with nogil:
            data = dispatch_source_get_data(self._source)
        return data


cdef class ProcessSource:
    """
    Dispatch source for monitoring process events.

    Monitors a process for specific events like exit, fork, exec, or signal.
    """
    cdef dispatch_source_t _source
    cdef object _handler
    cdef bint _started
    cdef bint _cancelled
    cdef int _pid
    cdef uintptr_t _events

    def __cinit__(self):
        self._source = NULL
        self._handler = None
        self._started = False
        self._cancelled = False
        self._pid = 0
        self._events = 0

    def __init__(self, int pid, handler, uintptr_t events=_DISPATCH_PROC_EXIT, Queue queue=None):
        """
        Create a new process source.

        Args:
            pid: The process ID to monitor.
            handler: Callable to invoke when an event occurs.
                     Receives no arguments.
            events: Events to monitor. Combine with bitwise OR:
                    - PROC_EXIT: Process exited
                    - PROC_FORK: Process forked
                    - PROC_EXEC: Process executed exec()
                    - PROC_SIGNAL: Process received a signal
            queue: Queue to execute handler on. If None, uses default global queue.
        """
        if not callable(handler):
            raise TypeError("handler must be callable")

        self._pid = pid
        self._events = events
        cdef dispatch_queue_t q
        if queue is not None:
            q = queue._queue
        else:
            q = NULL

        # Create process source
        with nogil:
            self._source = dispatch_source_create(
                _dispatch_source_type_proc, <uintptr_t>pid, events, q)

        if self._source == NULL:
            raise RuntimeError("Failed to create process source")

        # Store handler and set up callbacks
        self._handler = handler
        Py_INCREF(handler)

        cdef PyObject* ctx = <PyObject*>handler
        with nogil:
            dispatch_set_context(<dispatch_source_t>self._source, <void*>ctx)
            dispatch_source_set_event_handler_f(self._source, _python_timer_callback)
            dispatch_source_set_cancel_handler_f(self._source, _python_timer_cancel_callback)

    def __dealloc__(self):
        if self._source != NULL:
            if not self._cancelled:
                dispatch_source_cancel(self._source)
            if not self._started:
                dispatch_resume(<dispatch_queue_t>self._source)
            dispatch_release(<dispatch_queue_t>self._source)
            self._source = NULL

    def start(self):
        """Start monitoring the process."""
        if self._started:
            return
        if self._cancelled:
            raise RuntimeError("Cannot start a cancelled process source")
        self._started = True
        with nogil:
            dispatch_resume(<dispatch_queue_t>self._source)

    def cancel(self):
        """Stop monitoring the process."""
        if self._cancelled:
            return
        self._cancelled = True
        with nogil:
            dispatch_source_cancel(self._source)

    @property
    def is_cancelled(self):
        """Check if the source has been cancelled."""
        cdef intptr_t result
        with nogil:
            result = dispatch_source_testcancel(self._source)
        return result != 0

    @property
    def pid(self):
        """Get the process ID being monitored."""
        return self._pid

    @property
    def events_pending(self):
        """
        Get the events that have occurred since the last handler invocation.

        Returns a bitmask of PROC_* constants.
        """
        cdef uintptr_t data
        with nogil:
            data = dispatch_source_get_data(self._source)
        return data


cdef class Data:
    """
    Dispatch data object for efficient buffer management.

    Data objects are immutable containers for bytes that can be efficiently
    concatenated and sliced without copying the underlying data.
    """
    cdef dispatch_data_t _data
    cdef bint _owned

    def __cinit__(self):
        self._data = NULL
        self._owned = False

    def __init__(self, bytes data=None):
        """
        Create a new dispatch data object.

        Args:
            data: Optional bytes to wrap. If None, creates empty data.
        """
        cdef const char* buffer
        cdef size_t size

        if data is None or len(data) == 0:
            self._data = NULL
            self._owned = False
        else:
            buffer = data
            size = len(data)
            # Create a copy of the data (using default destructor)
            with nogil:
                self._data = dispatch_data_create(buffer, size, NULL, NULL)
            self._owned = True

    def __dealloc__(self):
        if self._data != NULL and self._owned:
            dispatch_release(<dispatch_queue_t>self._data)
            self._data = NULL

    def __len__(self):
        """Return the size of the data in bytes."""
        if self._data == NULL:
            return 0
        cdef size_t size
        with nogil:
            size = dispatch_data_get_size(self._data)
        return size

    @property
    def size(self):
        """Get the size of the data in bytes."""
        return len(self)

    def __bytes__(self):
        """Convert to bytes object."""
        if self._data == NULL:
            return b""
        cdef const void* buffer = NULL
        cdef size_t size = 0
        cdef dispatch_data_t mapped

        # Map the data to get contiguous access
        with nogil:
            mapped = dispatch_data_create_map(self._data, &buffer, &size)

        if mapped == NULL or buffer == NULL:
            return b""

        result = (<const char*>buffer)[:size]

        with nogil:
            dispatch_release(<dispatch_queue_t>mapped)

        return result

    def concat(self, Data other):
        """
        Concatenate this data with another.

        Args:
            other: Another Data object to append.

        Returns:
            A new Data object containing the concatenated data.
        """
        cdef Data result = Data.__new__(Data)

        if self._data == NULL and other._data == NULL:
            result._data = NULL
            result._owned = False
        elif self._data == NULL:
            with nogil:
                dispatch_retain(<dispatch_queue_t>other._data)
            result._data = other._data
            result._owned = True
        elif other._data == NULL:
            with nogil:
                dispatch_retain(<dispatch_queue_t>self._data)
            result._data = self._data
            result._owned = True
        else:
            with nogil:
                result._data = dispatch_data_create_concat(self._data, other._data)
            result._owned = True

        return result

    def subrange(self, size_t offset, size_t length):
        """
        Create a new Data object from a subrange of this data.

        Args:
            offset: Starting offset in bytes.
            length: Number of bytes to include.

        Returns:
            A new Data object containing the subrange.
        """
        cdef Data result = Data.__new__(Data)

        if self._data == NULL:
            result._data = NULL
            result._owned = False
        else:
            with nogil:
                result._data = dispatch_data_create_subrange(self._data, offset, length)
            result._owned = True

        return result

    def copy_region(self, size_t location):
        """
        Get the region containing a specific location.

        Dispatch data may be stored as discontiguous regions. This method
        returns the contiguous region that contains the specified byte offset.

        Args:
            location: Byte offset to look up.

        Returns:
            Tuple of (region_data: Data, region_offset: int) where:
            - region_data: The contiguous region containing the location
            - region_offset: Offset within the region where location falls

        Raises:
            ValueError: If location is out of bounds.
        """
        if self._data == NULL:
            raise ValueError("location out of bounds for empty data")

        cdef size_t region_offset = 0
        cdef dispatch_data_t region_data
        cdef Data result

        with nogil:
            region_data = dispatch_data_copy_region(self._data, location, &region_offset)

        if region_data == NULL:
            raise ValueError("location out of bounds")

        result = Data.__new__(Data)
        result._data = region_data
        result._owned = True
        return (result, region_offset)

    def apply(self, func):
        """
        Iterate over the contiguous regions of this data.

        Dispatch data may be stored as multiple discontiguous memory regions.
        This method calls the provided function for each contiguous region.

        Args:
            func: Callable(offset: int, data: bytes) -> bool
                  - offset: Byte offset of this region within the overall data
                  - data: The bytes in this contiguous region
                  - Return True to continue iteration, False to stop

        Returns:
            True if all regions were visited, False if iteration was stopped early.
        """
        if self._data == NULL:
            return True

        # Since dispatch_data_apply uses blocks, we'll implement this
        # by mapping the data and returning it as a single region.
        # For most cases, this is sufficient. True multi-region iteration
        # would require block support similar to IOChannel.
        cdef const void* buffer = NULL
        cdef size_t size = 0
        cdef dispatch_data_t mapped

        with nogil:
            mapped = dispatch_data_create_map(self._data, &buffer, &size)

        if mapped == NULL or buffer == NULL:
            return True

        try:
            chunk = (<const char*>buffer)[:size]
            result = func(0, chunk)
            return bool(result) if result is not None else True
        finally:
            with nogil:
                dispatch_release(<dispatch_queue_t>mapped)

    @staticmethod
    cdef Data _from_dispatch_data(dispatch_data_t data, bint owned):
        """Create a Data object from a dispatch_data_t (internal use)."""
        cdef Data result = Data.__new__(Data)
        result._data = data
        result._owned = owned
        return result


# I/O type constants
IO_STREAM = 0  # DISPATCH_IO_STREAM
IO_RANDOM = 1  # DISPATCH_IO_RANDOM
IO_STOP = 0x1  # DISPATCH_IO_STOP - close flag to cancel pending operations


# Trampoline for dispatch_read/dispatch_write handlers
cdef void _python_io_handler(dispatch_data_t data, int error) noexcept with gil:
    """Trampoline for async I/O completion handlers."""
    cdef object handler_tuple
    cdef object handler
    cdef object ctx_ptr

    # Get context (stored as tuple: (handler, context_id))
    # For now we use a simpler approach - the context is the handler itself
    pass  # This is handled differently below


# Storage for I/O callbacks (prevent garbage collection)
cdef dict _io_callbacks = {}
cdef int _io_callback_id = 0


cdef void _dispatch_read_handler(dispatch_data_t data, int error) noexcept with gil:
    """Handler for dispatch_read."""
    global _io_callback_id
    # This approach won't work well - we need to store context
    pass


# Simpler async I/O using completion handlers
def read_async(int fd, size_t length, handler, Queue queue=None):
    """
    Read data from a file descriptor asynchronously.

    Args:
        fd: File descriptor to read from.
        length: Maximum number of bytes to read.
        handler: Callable invoked with (data: bytes, error: int) when complete.
                 data is the bytes read, error is 0 on success.
        queue: Queue to execute handler on. If None, uses default global queue.
    """
    if not callable(handler):
        raise TypeError("handler must be callable")

    cdef dispatch_queue_t q
    if queue is not None:
        q = queue._queue
    else:
        with nogil:
            q = dispatch_get_global_queue(_DISPATCH_QUEUE_PRIORITY_DEFAULT, 0)

    # We need to use a workaround since dispatch_read uses blocks
    # For now, implement using ReadSource and os.read
    import os as _os

    def _do_read():
        try:
            data = _os.read(fd, length)
            handler(data, 0)
        except OSError as e:
            handler(b"", e.errno)

    cdef Queue wrap_queue
    if queue is not None:
        wrap_queue = queue
    else:
        wrap_queue = Queue.global_queue()

    wrap_queue.run_async(_do_read)


def write_async(int fd, bytes data, handler, Queue queue=None):
    """
    Write data to a file descriptor asynchronously.

    Args:
        fd: File descriptor to write to.
        data: Bytes to write.
        handler: Callable invoked with (remaining: bytes, error: int) when complete.
                 remaining is any unwritten data, error is 0 on success.
        queue: Queue to execute handler on. If None, uses default global queue.
    """
    if not callable(handler):
        raise TypeError("handler must be callable")

    import os as _os

    def _do_write():
        try:
            written = _os.write(fd, data)
            remaining = data[written:] if written < len(data) else b""
            handler(remaining, 0)
        except OSError as e:
            handler(data, e.errno)

    cdef Queue wrap_queue
    if queue is not None:
        wrap_queue = queue
    else:
        wrap_queue = Queue.global_queue()

    wrap_queue.run_async(_do_write)


cdef class Workloop:
    """
    Dispatch workloop for priority-inversion-avoiding execution.

    Workloops are specialized queues that avoid priority inversion by
    dynamically adjusting the priority of work items.
    """
    cdef dispatch_workloop_t _workloop
    cdef bint _owned
    cdef bint _inactive
    cdef bytes _label_bytes

    def __cinit__(self):
        self._workloop = NULL
        self._owned = False
        self._inactive = False

    def __init__(self, str label, bint inactive=False):
        """
        Create a new workloop.

        Args:
            label: String label for debugging.
            inactive: If True, create in inactive state. Must call activate()
                      before the workloop will process tasks.
        """
        cdef const char* c_label = NULL

        if label is not None:
            self._label_bytes = label.encode('utf-8')
            c_label = self._label_bytes

        if inactive:
            with nogil:
                self._workloop = dispatch_workloop_create_inactive(c_label)
            self._inactive = True
        else:
            # dispatch_workloop_create creates an inactive workloop that must be activated
            with nogil:
                self._workloop = dispatch_workloop_create(c_label)

        if self._workloop == NULL:
            raise RuntimeError("Failed to create workloop")

        self._owned = True

        # Activate non-inactive workloops immediately
        if not inactive:
            with nogil:
                dispatch_activate(<dispatch_queue_t>self._workloop)

    def __dealloc__(self):
        if self._workloop != NULL and self._owned:
            # Must activate inactive workloops before releasing
            # otherwise dispatch_release will block forever
            if self._inactive:
                dispatch_activate(<dispatch_queue_t>self._workloop)
            dispatch_release(<dispatch_queue_t>self._workloop)
            self._workloop = NULL

    def activate(self):
        """
        Activate an inactive workloop.

        Raises:
            RuntimeError: If the workloop was not created as inactive.
        """
        if not self._inactive:
            raise RuntimeError("Workloop was not created as inactive")
        with nogil:
            dispatch_activate(<dispatch_queue_t>self._workloop)
        self._inactive = False

    @property
    def is_inactive(self):
        """Check if the workloop is currently inactive."""
        return self._inactive

    def set_autorelease_frequency(self, unsigned int frequency):
        """
        Set the autorelease frequency for the workloop.

        This controls how often the workloop drains its autorelease pool,
        which is relevant when using Objective-C APIs from Python.

        Must be called while the workloop is inactive (before activation).

        Args:
            frequency: One of:
                - AUTORELEASE_FREQUENCY_INHERIT (0): Inherit from target queue
                - AUTORELEASE_FREQUENCY_WORK_ITEM (1): Drain after each work item
                - AUTORELEASE_FREQUENCY_NEVER (2): Never drain automatically

        Raises:
            RuntimeError: If the workloop has already been activated.
        """
        if not self._inactive:
            raise RuntimeError("Autorelease frequency can only be set on inactive workloops")
        with nogil:
            dispatch_workloop_set_autorelease_frequency(self._workloop, frequency)

    def run_async(self, func):
        """
        Submit a callable for asynchronous execution on the workloop.

        Args:
            func: A callable taking no arguments.

        Raises:
            RuntimeError: If the workloop is inactive.
        """
        if self._inactive:
            raise RuntimeError("Cannot submit work to an inactive workloop")
        if not callable(func):
            raise TypeError("func must be callable")
        Py_INCREF(func)
        cdef PyObject* ctx = <PyObject*>func
        with nogil:
            dispatch_async_f(<dispatch_queue_t>self._workloop, <void*>ctx, _python_callback)

    def run_sync(self, func):
        """
        Submit a callable for synchronous execution on the workloop.

        Note: Uses async + semaphore pattern since dispatch_sync_f can deadlock
        on workloops due to their specialized execution model.

        Args:
            func: A callable taking no arguments.

        Raises:
            RuntimeError: If the workloop is inactive.
        """
        if self._inactive:
            raise RuntimeError("Cannot submit work to an inactive workloop")
        if not callable(func):
            raise TypeError("func must be callable")

        # Use Python Semaphore to wait for completion
        sem = Semaphore(0)
        exception_info = [None]

        def wrapper():
            try:
                func()
            except Exception as e:
                exception_info[0] = e
            finally:
                sem.signal()

        self.run_async(wrapper)
        sem.wait()

        if exception_info[0] is not None:
            raise exception_info[0]


cdef class IOChannel:
    """
    High-performance asynchronous I/O channel using dispatch_io.

    IOChannel provides efficient async file I/O with automatic chunking,
    flow control via high/low water marks, and synchronization via barriers.

    Example:
        >>> fd = os.open("file.txt", os.O_RDONLY)
        >>> channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)
        >>> channel.set_high_water(4096)  # Read in 4KB chunks
        >>> def on_read(done, data, error):
        ...     if data:
        ...         print(f"Read {len(data)} bytes")
        ...     if done:
        ...         print("Read complete")
        >>> channel.read(1024*1024, on_read)  # Read up to 1MB
        >>> # ... wait for completion ...
        >>> channel.close()
        >>> os.close(fd)
    """
    cdef dispatch_io_t _channel
    cdef bint _owned
    cdef bint _closed
    cdef int _fd
    cdef unsigned long _cleanup_cb_id
    cdef object _cleanup_handler

    def __cinit__(self):
        self._channel = NULL
        self._owned = False
        self._closed = False
        self._fd = -1
        self._cleanup_cb_id = 0
        self._cleanup_handler = None

    def __init__(self, int fd, unsigned int io_type=0, Queue queue=None,
                 cleanup_handler=None):
        """
        Create an I/O channel for a file descriptor.

        Args:
            fd: File descriptor (must remain open while channel is active).
            io_type: IO_STREAM (0) for sequential I/O, IO_RANDOM (1) for
                     random access I/O with offsets.
            queue: Queue for cleanup handler execution (default: global queue).
            cleanup_handler: Optional callable(error: int) invoked when channel
                             is fully closed. error is 0 on success.

        Raises:
            RuntimeError: If channel creation fails.
            TypeError: If cleanup_handler is provided but not callable.
        """
        cdef dispatch_queue_t q
        cdef void* cleanup_block = NULL

        if cleanup_handler is not None and not callable(cleanup_handler):
            raise TypeError("cleanup_handler must be callable")

        if queue is not None:
            q = queue._queue
        else:
            with nogil:
                q = dispatch_get_global_queue(_DISPATCH_QUEUE_PRIORITY_DEFAULT, 0)

        # Register cleanup handler if provided
        if cleanup_handler is not None:
            self._cleanup_handler = cleanup_handler
            self._cleanup_cb_id = _register_io_callback(cleanup_handler)
            cleanup_block = _cygcd_create_cleanup_block_v2(self._cleanup_cb_id)

        # Create the channel
        with nogil:
            self._channel = dispatch_io_create(io_type, fd, q, <void*>cleanup_block)

        if self._channel == NULL:
            # Clean up the block and callback if channel creation failed
            if cleanup_block != NULL:
                _cygcd_release_block(cleanup_block)
                _unregister_io_callback(self._cleanup_cb_id)
            raise RuntimeError("Failed to create I/O channel")

        self._fd = fd
        self._owned = True

    def __dealloc__(self):
        if self._channel != NULL and self._owned:
            if not self._closed:
                with nogil:
                    dispatch_io_close(self._channel, 0)
            with nogil:
                dispatch_release(<dispatch_queue_t>self._channel)
            self._channel = NULL

    def read(self, size_t length, handler, off_t offset=0, Queue queue=None):
        """
        Read data asynchronously from the channel.

        The handler may be called multiple times with chunks of data.
        When done=True, the read operation is complete.

        Args:
            length: Maximum bytes to read. Use a large value to read all available.
            handler: Callable(done: bool, data: bytes, error: int).
                     - done: True when read is complete or error occurred.
                     - data: Bytes read (may be empty on final call or error).
                     - error: 0 on success, errno on failure.
            offset: File offset for IO_RANDOM channels (ignored for IO_STREAM).
            queue: Queue for handler execution (default: global queue).

        Raises:
            RuntimeError: If channel is closed.
            TypeError: If handler is not callable.
        """
        if self._closed:
            raise RuntimeError("Channel is closed")
        if not callable(handler):
            raise TypeError("handler must be callable")

        cdef dispatch_queue_t q
        if queue is not None:
            q = queue._queue
        else:
            with nogil:
                q = dispatch_get_global_queue(_DISPATCH_QUEUE_PRIORITY_DEFAULT, 0)

        # Register callback and create block
        cdef unsigned long cb_id = _register_io_callback(handler)
        cdef void* block = _cygcd_create_io_block(cb_id)

        with nogil:
            dispatch_io_read(self._channel, offset, length, q, <void*>block)

        # Note: Block is retained by GCD, will be released when done

    def write(self, bytes data, handler, off_t offset=0, Queue queue=None):
        """
        Write data asynchronously to the channel.

        The handler may be called multiple times as data is written.
        When done=True, the write operation is complete.

        Args:
            data: Bytes to write.
            handler: Callable(done: bool, remaining: bytes, error: int).
                     - done: True when write is complete or error occurred.
                     - remaining: Bytes not yet written (empty when complete).
                     - error: 0 on success, errno on failure.
            offset: File offset for IO_RANDOM channels (ignored for IO_STREAM).
            queue: Queue for handler execution (default: global queue).

        Raises:
            RuntimeError: If channel is closed.
            TypeError: If handler is not callable or data is not bytes.
        """
        if self._closed:
            raise RuntimeError("Channel is closed")
        if not callable(handler):
            raise TypeError("handler must be callable")
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")

        cdef dispatch_queue_t q
        if queue is not None:
            q = queue._queue
        else:
            with nogil:
                q = dispatch_get_global_queue(_DISPATCH_QUEUE_PRIORITY_DEFAULT, 0)

        # Create dispatch_data from bytes
        cdef const char* buffer = data
        cdef size_t size = len(data)
        cdef dispatch_data_t dispatch_data

        with nogil:
            dispatch_data = dispatch_data_create(buffer, size, NULL, NULL)

        if dispatch_data == NULL:
            raise RuntimeError("Failed to create dispatch data")

        # Register callback and create block
        cdef unsigned long cb_id = _register_io_callback(handler)
        cdef void* block = _cygcd_create_io_block(cb_id)

        with nogil:
            dispatch_io_write(self._channel, offset, dispatch_data, q, <void*>block)
            # Release our reference to dispatch_data (GCD retains it)
            dispatch_release(<dispatch_queue_t>dispatch_data)

    def close(self, bint stop=False):
        """
        Close the I/O channel.

        Args:
            stop: If True, cancel pending operations immediately (IO_STOP).
                  If False, allow pending operations to complete.
        """
        if self._closed:
            return

        cdef unsigned int flags = 0
        if stop:
            flags = DISPATCH_IO_STOP

        with nogil:
            dispatch_io_close(self._channel, flags)

        self._closed = True

    def set_high_water(self, size_t size):
        """
        Set the high water mark for I/O operations.

        The high water mark determines the maximum number of bytes to
        deliver per handler invocation. Useful for processing large
        files in chunks.

        Args:
            size: Maximum bytes per handler call.
        """
        if self._closed:
            raise RuntimeError("Channel is closed")
        with nogil:
            dispatch_io_set_high_water(self._channel, size)

    def set_low_water(self, size_t size):
        """
        Set the low water mark for I/O operations.

        The low water mark determines the minimum number of bytes to
        accumulate before invoking the handler (except for final delivery).

        Args:
            size: Minimum bytes before handler invocation.
        """
        if self._closed:
            raise RuntimeError("Channel is closed")
        with nogil:
            dispatch_io_set_low_water(self._channel, size)

    def set_interval(self, uint64_t interval_ns, unsigned int flags=0):
        """
        Set the delivery interval for I/O operations.

        Allows batching of I/O operations for efficiency.

        Args:
            interval_ns: Interval in nanoseconds.
            flags: Optional flags (currently unused, pass 0).
        """
        if self._closed:
            raise RuntimeError("Channel is closed")
        with nogil:
            dispatch_io_set_interval(self._channel, interval_ns, flags)

    def barrier(self, handler):
        """
        Execute a handler when all pending I/O operations complete.

        The barrier handler is executed after all previously submitted
        read and write operations have completed.

        Args:
            handler: Callable with no arguments.

        Raises:
            RuntimeError: If channel is closed.
            TypeError: If handler is not callable.
        """
        if self._closed:
            raise RuntimeError("Channel is closed")
        if not callable(handler):
            raise TypeError("handler must be callable")

        # Register callback and create block
        cdef unsigned long cb_id = _register_io_callback(handler)
        cdef void* block = _cygcd_create_barrier_block(cb_id)

        with nogil:
            dispatch_io_barrier(self._channel, <void*>block)

    @property
    def fd(self):
        """The file descriptor associated with this channel."""
        return self._fd

    @property
    def is_closed(self):
        """Check if the channel has been closed."""
        return self._closed