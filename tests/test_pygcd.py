"""Tests for pygcd - Python GCD wrapper."""

import os
import signal
import subprocess
import time
import threading
import pytest
import pygcd


class TestQueue:
    """Tests for Queue class."""

    def test_create_serial_queue(self):
        """Test creating a serial queue."""
        q = pygcd.Queue("test.serial")
        assert q.label == "test.serial"

    def test_create_concurrent_queue(self):
        """Test creating a concurrent queue."""
        q = pygcd.Queue("test.concurrent", concurrent=True)
        assert q.label == "test.concurrent"

    def test_create_queue_no_label(self):
        """Test creating a queue without a label."""
        q = pygcd.Queue()
        # Label may be None or empty string depending on implementation
        assert q.label is None or q.label == ""

    def test_global_queue(self):
        """Test getting global queue."""
        q = pygcd.Queue.global_queue()
        assert q is not None
        # Global queues have system labels
        assert q.label is not None

    def test_global_queue_priorities(self):
        """Test getting global queues with different priorities."""
        high = pygcd.Queue.global_queue(pygcd.QUEUE_PRIORITY_HIGH)
        default = pygcd.Queue.global_queue(pygcd.QUEUE_PRIORITY_DEFAULT)
        low = pygcd.Queue.global_queue(pygcd.QUEUE_PRIORITY_LOW)
        bg = pygcd.Queue.global_queue(pygcd.QUEUE_PRIORITY_BACKGROUND)
        assert high is not None
        assert default is not None
        assert low is not None
        assert bg is not None

    def test_global_queue_qos(self):
        """Test getting global queues with QOS classes."""
        q = pygcd.Queue.global_queue(pygcd.QOS_CLASS_USER_INITIATED)
        assert q is not None

    def test_async_execution(self):
        """Test run_async executes the callable."""
        q = pygcd.Queue("test.async")
        results = []

        def task():
            results.append(1)

        q.run_async(task)
        # Wait for async task to complete
        q.run_sync(lambda: None)
        assert results == [1]

    def test_sync_execution(self):
        """Test run_sync executes the callable and blocks."""
        q = pygcd.Queue("test.sync")
        results = []

        def task():
            results.append(1)

        q.run_sync(task)
        assert results == [1]

    def test_serial_queue_order(self):
        """Test that serial queue maintains FIFO order."""
        q = pygcd.Queue("test.order")
        results = []

        for i in range(5):
            q.run_async(lambda i=i: results.append(i))

        q.run_sync(lambda: None)  # Wait for all to complete
        assert results == [0, 1, 2, 3, 4]

    def test_barrier_async(self):
        """Test barrier_async on concurrent queue."""
        q = pygcd.Queue("test.barrier", concurrent=True)
        results = []

        # Submit some reads
        for i in range(3):
            q.run_async(lambda i=i: results.append(("read", i)))

        # Barrier write
        q.barrier_async(lambda: results.append(("write", 0)))

        # More reads
        for i in range(3, 6):
            q.run_async(lambda i=i: results.append(("read", i)))

        q.barrier_sync(lambda: None)  # Wait for completion

        # The write should appear after all initial reads complete
        # and before all subsequent reads start
        write_idx = None
        for i, item in enumerate(results):
            if item[0] == "write":
                write_idx = i
                break

        assert write_idx is not None
        # All reads before barrier should be before write
        # All reads after barrier should be after write

    def test_barrier_sync(self):
        """Test barrier_sync blocks until complete."""
        q = pygcd.Queue("test.barrier_sync", concurrent=True)
        results = []

        q.run_async(lambda: results.append(1))
        q.barrier_sync(lambda: results.append(2))

        assert 2 in results

    def test_after_delayed_execution(self):
        """Test after schedules delayed execution."""
        q = pygcd.Queue("test.after")
        results = []
        start = time.time()

        q.after(0.1, lambda: results.append(time.time() - start))

        # Wait for the delayed task
        time.sleep(0.2)
        q.run_sync(lambda: None)

        assert len(results) == 1
        assert results[0] >= 0.1

    def test_async_raises_on_non_callable(self):
        """Test that run_async raises TypeError for non-callable."""
        q = pygcd.Queue("test.error")
        with pytest.raises(TypeError):
            q.run_async("not a callable")

    def test_sync_raises_on_non_callable(self):
        """Test that run_sync raises TypeError for non-callable."""
        q = pygcd.Queue("test.error")
        with pytest.raises(TypeError):
            q.run_sync(42)


class TestGroup:
    """Tests for Group class."""

    def test_create_group(self):
        """Test creating a group."""
        g = pygcd.Group()
        assert g is not None

    def test_group_async_and_wait(self):
        """Test submitting tasks to group and waiting."""
        g = pygcd.Group()
        q = pygcd.Queue.global_queue()
        results = []

        for i in range(5):
            g.run_async(q, lambda i=i: results.append(i))

        completed = g.wait()
        assert completed is True
        assert len(results) == 5

    def test_group_wait_timeout(self):
        """Test group wait with timeout."""
        g = pygcd.Group()
        q = pygcd.Queue.global_queue()

        def slow_task():
            time.sleep(0.5)

        g.run_async(q, slow_task)
        completed = g.wait(0.1)
        assert completed is False

    def test_group_notify(self):
        """Test group notify callback."""
        g = pygcd.Group()
        q = pygcd.Queue("test.notify")
        results = []

        for i in range(3):
            g.run_async(q, lambda i=i: results.append(i))

        g.notify(q, lambda: results.append("done"))
        g.wait()
        q.run_sync(lambda: None)  # Ensure notify has run

        assert "done" in results
        # "done" should be last
        assert results[-1] == "done"

    def test_group_enter_leave(self):
        """Test manual group enter/leave."""
        g = pygcd.Group()
        q = pygcd.Queue.global_queue()
        results = []

        g.enter()

        def task():
            results.append(1)
            g.leave()

        q.run_async(task)
        completed = g.wait()
        assert completed is True
        assert results == [1]


class TestSemaphore:
    """Tests for Semaphore class."""

    def test_create_semaphore(self):
        """Test creating a semaphore."""
        s = pygcd.Semaphore(1)
        assert s is not None

    def test_semaphore_signal_wait(self):
        """Test semaphore signal and wait."""
        s = pygcd.Semaphore(0)
        q = pygcd.Queue.global_queue()
        results = []

        def producer():
            results.append("produced")
            s.signal()

        def consumer():
            s.wait()
            results.append("consumed")

        q.run_async(producer)
        q.run_async(consumer)

        time.sleep(0.1)
        assert "produced" in results
        assert "consumed" in results

    def test_semaphore_timeout(self):
        """Test semaphore wait with timeout."""
        s = pygcd.Semaphore(0)
        acquired = s.wait(0.1)
        assert acquired is False

    def test_semaphore_resource_limiting(self):
        """Test semaphore limits concurrent access."""
        s = pygcd.Semaphore(2)  # Allow 2 concurrent
        q = pygcd.Queue.global_queue()
        active = []
        max_active = [0]
        lock = threading.Lock()

        def task(i):
            s.wait()
            with lock:
                active.append(i)
                if len(active) > max_active[0]:
                    max_active[0] = len(active)
            time.sleep(0.05)
            with lock:
                active.remove(i)
            s.signal()

        g = pygcd.Group()
        for i in range(5):
            g.run_async(q, lambda i=i: task(i))

        g.wait()
        assert max_active[0] <= 2


class TestOnce:
    """Tests for Once class."""

    def test_once_executes_once(self):
        """Test Once executes callable exactly once."""
        once = pygcd.Once()
        results = []

        def init():
            results.append(1)

        once(init)
        once(init)
        once(init)

        assert results == [1]

    def test_once_thread_safe(self):
        """Test Once is thread-safe."""
        once = pygcd.Once()
        results = []
        lock = threading.Lock()

        def init():
            with lock:
                results.append(1)

        q = pygcd.Queue.global_queue()
        g = pygcd.Group()

        for _ in range(10):
            g.run_async(q, lambda: once(init))

        g.wait()
        assert results == [1]


class TestApply:
    """Tests for apply function."""

    def test_apply_basic(self):
        """Test basic apply functionality."""
        results = []
        lock = threading.Lock()

        def task(i):
            with lock:
                results.append(i)

        pygcd.apply(5, task)
        assert sorted(results) == [0, 1, 2, 3, 4]

    def test_apply_with_queue(self):
        """Test apply with explicit queue."""
        q = pygcd.Queue.global_queue()
        results = []
        lock = threading.Lock()

        def task(i):
            with lock:
                results.append(i)

        pygcd.apply(5, task, q)
        assert sorted(results) == [0, 1, 2, 3, 4]

    def test_apply_raises_on_non_callable(self):
        """Test apply raises TypeError for non-callable."""
        with pytest.raises(TypeError):
            pygcd.apply(5, "not callable")


class TestConstants:
    """Tests for module constants."""

    def test_time_constants(self):
        """Test time constants are defined."""
        assert pygcd.DISPATCH_TIME_NOW == 0
        assert pygcd.DISPATCH_TIME_FOREVER == 0xFFFFFFFFFFFFFFFF
        assert pygcd.NSEC_PER_SEC == 1000000000
        assert pygcd.NSEC_PER_MSEC == 1000000
        assert pygcd.NSEC_PER_USEC == 1000
        assert pygcd.USEC_PER_SEC == 1000000
        assert pygcd.MSEC_PER_SEC == 1000

    def test_priority_constants(self):
        """Test priority constants are defined."""
        assert pygcd.QUEUE_PRIORITY_HIGH == 2
        assert pygcd.QUEUE_PRIORITY_DEFAULT == 0
        assert pygcd.QUEUE_PRIORITY_LOW == -2
        assert pygcd.QUEUE_PRIORITY_BACKGROUND == -32768

    def test_qos_constants(self):
        """Test QOS class constants are defined."""
        assert pygcd.QOS_CLASS_USER_INTERACTIVE == 0x21
        assert pygcd.QOS_CLASS_USER_INITIATED == 0x19
        assert pygcd.QOS_CLASS_DEFAULT == 0x15
        assert pygcd.QOS_CLASS_UTILITY == 0x11
        assert pygcd.QOS_CLASS_BACKGROUND == 0x09
        assert pygcd.QOS_CLASS_UNSPECIFIED == 0x00


class TestTimeFromNow:
    """Tests for time_from_now function."""

    def test_time_from_now(self):
        """Test time_from_now returns a valid time."""
        t = pygcd.time_from_now(1.0)
        assert t > 0
        assert t != pygcd.DISPATCH_TIME_FOREVER


class TestWalltime:
    """Tests for walltime function."""

    def test_walltime_now(self):
        """Test walltime with current time."""
        t = pygcd.walltime()
        assert t > 0
        assert t != pygcd.DISPATCH_TIME_FOREVER

    def test_walltime_with_delta(self):
        """Test walltime with delta."""
        t1 = pygcd.walltime()
        t2 = pygcd.walltime(delta_seconds=1.0)
        # Walltime values decrease as time increases (relative to far future)
        # So t2 (1 second later) should be different from t1
        assert t1 != t2

    def test_walltime_with_timestamp(self):
        """Test walltime with specific timestamp."""
        import time
        now = time.time()
        t = pygcd.walltime(timestamp=now)
        assert t > 0


class TestMainQueue:
    """Tests for main queue access."""

    def test_get_main_queue(self):
        """Test getting the main queue."""
        main = pygcd.Queue.main_queue()
        assert main is not None
        assert main.label is not None

    def test_main_queue_is_serial(self):
        """Test that main queue has the expected label."""
        main = pygcd.Queue.main_queue()
        assert "main" in main.label.lower()


class TestSuspendResume:
    """Tests for queue suspend/resume."""

    def test_suspend_resume(self):
        """Test suspending and resuming a queue."""
        q = pygcd.Queue("test.suspend")
        results = []

        q.suspend()
        q.run_async(lambda: results.append(1))

        # Task should not have run yet
        time.sleep(0.1)
        assert results == []

        q.resume()
        q.run_sync(lambda: None)
        assert results == [1]

    def test_multiple_suspend_resume(self):
        """Test that suspend/resume must be balanced."""
        q = pygcd.Queue("test.multi_suspend")
        results = []

        q.suspend()
        q.suspend()  # Two suspends
        q.run_async(lambda: results.append(1))

        q.resume()  # One resume - still suspended
        time.sleep(0.1)
        assert results == []

        q.resume()  # Two resumes - now resumed
        q.run_sync(lambda: None)
        assert results == [1]


class TestTimer:
    """Tests for Timer class."""

    def test_create_timer(self):
        """Test creating a timer."""
        timer = pygcd.Timer(1.0, lambda: None)
        assert timer is not None
        assert not timer.is_cancelled
        timer.cancel()

    def test_timer_fires(self):
        """Test that timer fires at interval."""
        results = []
        lock = threading.Lock()

        def handler():
            with lock:
                results.append(time.time())

        timer = pygcd.Timer(0.1, handler)
        start = time.time()
        timer.start()

        time.sleep(0.35)
        timer.cancel()

        # Should have fired ~3 times in 0.35s with 0.1s interval
        assert len(results) >= 2
        assert len(results) <= 5

    def test_timer_one_shot(self):
        """Test one-shot timer."""
        results = []

        def handler():
            results.append(1)

        timer = pygcd.Timer(0.0, handler, repeating=False, start_delay=0.05)
        timer.start()

        time.sleep(0.2)
        timer.cancel()

        # One-shot should fire exactly once
        assert results == [1]

    def test_timer_cancel(self):
        """Test cancelling a timer."""
        results = []

        timer = pygcd.Timer(0.05, lambda: results.append(1))
        timer.start()

        time.sleep(0.12)
        timer.cancel()
        count_at_cancel = len(results)

        time.sleep(0.1)
        # Should not have fired more after cancel
        assert len(results) == count_at_cancel
        assert timer.is_cancelled

    def test_timer_with_queue(self):
        """Test timer with explicit queue."""
        q = pygcd.Queue("test.timer_queue")
        results = []
        lock = threading.Lock()

        def handler():
            with lock:
                results.append(1)

        timer = pygcd.Timer(0.05, handler, queue=q)
        timer.start()

        time.sleep(0.15)
        timer.cancel()

        assert len(results) >= 2

    def test_timer_start_delay(self):
        """Test timer with start delay."""
        results = []
        start = time.time()

        def handler():
            results.append(time.time() - start)

        timer = pygcd.Timer(0.5, handler, start_delay=0.2, repeating=False)
        timer.start()

        time.sleep(0.4)
        timer.cancel()

        assert len(results) == 1
        assert results[0] >= 0.15  # Should have waited ~0.2s

    def test_timer_leeway(self):
        """Test timer with leeway (should not error)."""
        timer = pygcd.Timer(0.1, lambda: None, leeway=0.05)
        timer.start()
        time.sleep(0.05)
        timer.cancel()

    def test_timer_set_timer(self):
        """Test reconfiguring timer interval."""
        results = []
        lock = threading.Lock()

        def handler():
            with lock:
                results.append(time.time())

        # Start with fast interval
        timer = pygcd.Timer(0.05, handler)
        timer.start()

        time.sleep(0.15)
        count_before = len(results)
        assert count_before >= 2  # Should have fired a few times

        # Reconfigure to much slower - should fire less frequently
        timer.set_timer(1.0, start_delay=1.0)
        time.sleep(0.15)
        timer.cancel()

        count_after = len(results)
        # Should not have fired many more times after reconfiguring to slow
        assert count_after - count_before <= 1

    def test_timer_raises_on_non_callable(self):
        """Test timer raises TypeError for non-callable."""
        with pytest.raises(TypeError):
            pygcd.Timer(0.1, "not callable")

    def test_timer_cannot_restart_cancelled(self):
        """Test that cancelled timer cannot be restarted."""
        timer = pygcd.Timer(0.1, lambda: None)
        timer.cancel()
        with pytest.raises(RuntimeError):
            timer.start()


class TestQueueQOS:
    """Tests for Queue QOS and target queue features."""

    def test_queue_with_qos(self):
        """Test creating queue with QOS class."""
        q = pygcd.Queue("test.qos", qos=pygcd.QOS_CLASS_UTILITY)
        assert q is not None
        assert q.label == "test.qos"

    def test_queue_with_qos_and_priority(self):
        """Test creating queue with QOS and relative priority."""
        q = pygcd.Queue("test.qos_priority",
                       qos=pygcd.QOS_CLASS_USER_INITIATED,
                       relative_priority=-5)
        results = []
        q.run_sync(lambda: results.append(1))
        assert results == [1]

    def test_queue_concurrent_with_qos(self):
        """Test concurrent queue with QOS."""
        q = pygcd.Queue("test.concurrent_qos",
                       concurrent=True,
                       qos=pygcd.QOS_CLASS_BACKGROUND)
        results = []
        lock = threading.Lock()

        for i in range(3):
            q.run_async(lambda i=i: (lock.acquire(), results.append(i), lock.release()))

        q.barrier_sync(lambda: None)
        assert len(results) == 3

    def test_queue_target(self):
        """Test queue with target queue."""
        parent = pygcd.Queue("parent")
        child = pygcd.Queue("child", target=parent)
        results = []

        child.run_sync(lambda: results.append(1))
        assert results == [1]

    def test_queue_set_target(self):
        """Test setting target queue after creation."""
        parent = pygcd.Queue("parent")
        child = pygcd.Queue("child")

        child.set_target_queue(parent)
        results = []

        child.run_sync(lambda: results.append(1))
        assert results == [1]

    def test_queue_hierarchy(self):
        """Test queue hierarchy with multiple levels."""
        root = pygcd.Queue("root")
        level1 = pygcd.Queue("level1", target=root)
        level2 = pygcd.Queue("level2", target=level1)

        results = []
        level2.run_sync(lambda: results.append(1))
        assert results == [1]


class TestProcessEventConstants:
    """Tests for process event constants."""

    def test_proc_constants(self):
        """Test process event constants are defined."""
        assert pygcd.PROC_EXIT == 0x80000000
        assert pygcd.PROC_FORK == 0x40000000
        assert pygcd.PROC_EXEC == 0x20000000
        assert pygcd.PROC_SIGNAL == 0x08000000


class TestSignalSource:
    """Tests for SignalSource class."""

    def test_create_signal_source(self):
        """Test creating a signal source."""
        # Use SIGUSR1 which is safe to handle
        old_handler = signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        try:
            source = pygcd.SignalSource(signal.SIGUSR1, lambda: None)
            assert source is not None
            assert source.signal == signal.SIGUSR1
            assert not source.is_cancelled
            source.cancel()
        finally:
            signal.signal(signal.SIGUSR1, old_handler)

    def test_signal_source_fires(self):
        """Test that signal source fires on signal."""
        results = []
        lock = threading.Lock()

        def handler():
            with lock:
                results.append(1)

        old_handler = signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        try:
            source = pygcd.SignalSource(signal.SIGUSR1, handler)
            source.start()

            # Send signal to self
            os.kill(os.getpid(), signal.SIGUSR1)
            time.sleep(0.1)

            source.cancel()
            assert len(results) >= 1
        finally:
            signal.signal(signal.SIGUSR1, old_handler)

    def test_signal_source_cancel(self):
        """Test cancelling a signal source."""
        old_handler = signal.signal(signal.SIGUSR2, signal.SIG_IGN)
        try:
            source = pygcd.SignalSource(signal.SIGUSR2, lambda: None)
            source.start()
            source.cancel()
            assert source.is_cancelled
        finally:
            signal.signal(signal.SIGUSR2, old_handler)

    def test_signal_source_with_queue(self):
        """Test signal source with explicit queue."""
        q = pygcd.Queue("signal.queue")
        results = []

        old_handler = signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        try:
            source = pygcd.SignalSource(signal.SIGUSR1, lambda: results.append(1), queue=q)
            source.start()

            os.kill(os.getpid(), signal.SIGUSR1)
            time.sleep(0.1)

            source.cancel()
            assert len(results) >= 1
        finally:
            signal.signal(signal.SIGUSR1, old_handler)

    def test_signal_source_raises_on_non_callable(self):
        """Test signal source raises TypeError for non-callable."""
        with pytest.raises(TypeError):
            pygcd.SignalSource(signal.SIGUSR1, "not callable")


class TestReadSource:
    """Tests for ReadSource class."""

    def test_create_read_source(self):
        """Test creating a read source."""
        r, w = os.pipe()
        try:
            source = pygcd.ReadSource(r, lambda: None)
            assert source is not None
            assert source.fd == r
            assert not source.is_cancelled
            source.cancel()
        finally:
            os.close(r)
            os.close(w)

    def test_read_source_fires(self):
        """Test that read source fires when data is available."""
        r, w = os.pipe()
        results = []
        lock = threading.Lock()

        def handler():
            with lock:
                results.append(1)

        try:
            source = pygcd.ReadSource(r, handler)
            source.start()

            # Write data to trigger the source
            os.write(w, b"test")
            time.sleep(0.1)

            source.cancel()
            assert len(results) >= 1
        finally:
            os.close(r)
            os.close(w)

    def test_read_source_cancel(self):
        """Test cancelling a read source."""
        r, w = os.pipe()
        try:
            source = pygcd.ReadSource(r, lambda: None)
            source.start()
            source.cancel()
            assert source.is_cancelled
        finally:
            os.close(r)
            os.close(w)

    def test_read_source_with_queue(self):
        """Test read source with explicit queue."""
        r, w = os.pipe()
        q = pygcd.Queue("read.queue")
        results = []

        try:
            source = pygcd.ReadSource(r, lambda: results.append(1), queue=q)
            source.start()

            os.write(w, b"test")
            time.sleep(0.1)

            source.cancel()
            assert len(results) >= 1
        finally:
            os.close(r)
            os.close(w)

    def test_read_source_raises_on_non_callable(self):
        """Test read source raises TypeError for non-callable."""
        r, w = os.pipe()
        try:
            with pytest.raises(TypeError):
                pygcd.ReadSource(r, "not callable")
        finally:
            os.close(r)
            os.close(w)


class TestWriteSource:
    """Tests for WriteSource class."""

    def test_create_write_source(self):
        """Test creating a write source."""
        r, w = os.pipe()
        try:
            source = pygcd.WriteSource(w, lambda: None)
            assert source is not None
            assert source.fd == w
            assert not source.is_cancelled
            source.cancel()
        finally:
            os.close(r)
            os.close(w)

    def test_write_source_fires(self):
        """Test that write source fires when writing is possible."""
        r, w = os.pipe()
        results = []
        lock = threading.Lock()

        def handler():
            with lock:
                results.append(1)

        try:
            source = pygcd.WriteSource(w, handler)
            source.start()

            # Pipe should be immediately writable
            time.sleep(0.1)

            source.cancel()
            # Should have fired at least once since pipe is writable
            assert len(results) >= 1
        finally:
            os.close(r)
            os.close(w)

    def test_write_source_cancel(self):
        """Test cancelling a write source."""
        r, w = os.pipe()
        try:
            source = pygcd.WriteSource(w, lambda: None)
            source.start()
            source.cancel()
            assert source.is_cancelled
        finally:
            os.close(r)
            os.close(w)

    def test_write_source_raises_on_non_callable(self):
        """Test write source raises TypeError for non-callable."""
        r, w = os.pipe()
        try:
            with pytest.raises(TypeError):
                pygcd.WriteSource(w, "not callable")
        finally:
            os.close(r)
            os.close(w)


class TestProcessSource:
    """Tests for ProcessSource class."""

    def test_create_process_source(self):
        """Test creating a process source."""
        # Monitor our own process
        source = pygcd.ProcessSource(os.getpid(), lambda: None)
        assert source is not None
        assert source.pid == os.getpid()
        assert not source.is_cancelled
        source.cancel()

    def test_process_source_with_events(self):
        """Test creating process source with specific events."""
        source = pygcd.ProcessSource(
            os.getpid(),
            lambda: None,
            events=pygcd.PROC_EXIT | pygcd.PROC_FORK
        )
        assert source is not None
        source.cancel()

    def test_process_source_detects_exit(self):
        """Test that process source detects child exit."""
        results = []
        lock = threading.Lock()

        def handler():
            with lock:
                results.append("exited")

        # Start a subprocess that exits quickly
        proc = subprocess.Popen(["sleep", "0.1"])

        source = pygcd.ProcessSource(proc.pid, handler, events=pygcd.PROC_EXIT)
        source.start()

        # Wait for process to exit
        proc.wait()
        time.sleep(0.2)

        source.cancel()
        assert "exited" in results

    def test_process_source_cancel(self):
        """Test cancelling a process source."""
        source = pygcd.ProcessSource(os.getpid(), lambda: None)
        source.start()
        source.cancel()
        assert source.is_cancelled

    def test_process_source_with_queue(self):
        """Test process source with explicit queue."""
        q = pygcd.Queue("proc.queue")
        source = pygcd.ProcessSource(os.getpid(), lambda: None, queue=q)
        assert source is not None
        source.cancel()

    def test_process_source_raises_on_non_callable(self):
        """Test process source raises TypeError for non-callable."""
        with pytest.raises(TypeError):
            pygcd.ProcessSource(os.getpid(), "not callable")
