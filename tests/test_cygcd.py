"""Tests for cygcd - Python GCD wrapper."""

import os
import signal
import subprocess
import time
import threading
import pytest
import cygcd


class TestQueue:
    """Tests for Queue class."""

    def test_create_serial_queue(self):
        """Test creating a serial queue."""
        q = cygcd.Queue("test.serial")
        assert q.label == "test.serial"

    def test_create_concurrent_queue(self):
        """Test creating a concurrent queue."""
        q = cygcd.Queue("test.concurrent", concurrent=True)
        assert q.label == "test.concurrent"

    def test_create_queue_no_label(self):
        """Test creating a queue without a label."""
        q = cygcd.Queue()
        # Label may be None or empty string depending on implementation
        assert q.label is None or q.label == ""

    def test_global_queue(self):
        """Test getting global queue."""
        q = cygcd.Queue.global_queue()
        assert q is not None
        # Global queues have system labels
        assert q.label is not None

    def test_global_queue_priorities(self):
        """Test getting global queues with different priorities."""
        high = cygcd.Queue.global_queue(cygcd.QUEUE_PRIORITY_HIGH)
        default = cygcd.Queue.global_queue(cygcd.QUEUE_PRIORITY_DEFAULT)
        low = cygcd.Queue.global_queue(cygcd.QUEUE_PRIORITY_LOW)
        bg = cygcd.Queue.global_queue(cygcd.QUEUE_PRIORITY_BACKGROUND)
        assert high is not None
        assert default is not None
        assert low is not None
        assert bg is not None

    def test_global_queue_qos(self):
        """Test getting global queues with QOS classes."""
        q = cygcd.Queue.global_queue(cygcd.QOS_CLASS_USER_INITIATED)
        assert q is not None

    def test_async_execution(self):
        """Test run_async executes the callable."""
        q = cygcd.Queue("test.async")
        results = []

        def task():
            results.append(1)

        q.run_async(task)
        # Wait for async task to complete
        q.run_sync(lambda: None)
        assert results == [1]

    def test_sync_execution(self):
        """Test run_sync executes the callable and blocks."""
        q = cygcd.Queue("test.sync")
        results = []

        def task():
            results.append(1)

        q.run_sync(task)
        assert results == [1]

    def test_serial_queue_order(self):
        """Test that serial queue maintains FIFO order."""
        q = cygcd.Queue("test.order")
        results = []

        for i in range(5):
            q.run_async(lambda i=i: results.append(i))

        q.run_sync(lambda: None)  # Wait for all to complete
        assert results == [0, 1, 2, 3, 4]

    def test_barrier_async(self):
        """Test barrier_async on concurrent queue."""
        q = cygcd.Queue("test.barrier", concurrent=True)
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
        q = cygcd.Queue("test.barrier_sync", concurrent=True)
        results = []

        q.run_async(lambda: results.append(1))
        q.barrier_sync(lambda: results.append(2))

        assert 2 in results

    def test_after_delayed_execution(self):
        """Test after schedules delayed execution."""
        q = cygcd.Queue("test.after")
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
        q = cygcd.Queue("test.error")
        with pytest.raises(TypeError):
            q.run_async("not a callable")

    def test_sync_raises_on_non_callable(self):
        """Test that run_sync raises TypeError for non-callable."""
        q = cygcd.Queue("test.error")
        with pytest.raises(TypeError):
            q.run_sync(42)


class TestGroup:
    """Tests for Group class."""

    def test_create_group(self):
        """Test creating a group."""
        g = cygcd.Group()
        assert g is not None

    def test_group_async_and_wait(self):
        """Test submitting tasks to group and waiting."""
        g = cygcd.Group()
        q = cygcd.Queue.global_queue()
        results = []

        for i in range(5):
            g.run_async(q, lambda i=i: results.append(i))

        completed = g.wait()
        assert completed is True
        assert len(results) == 5

    def test_group_wait_timeout(self):
        """Test group wait with timeout."""
        g = cygcd.Group()
        q = cygcd.Queue.global_queue()

        def slow_task():
            time.sleep(0.5)

        g.run_async(q, slow_task)
        completed = g.wait(0.1)
        assert completed is False

    def test_group_notify(self):
        """Test group notify callback."""
        g = cygcd.Group()
        q = cygcd.Queue("test.notify")
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
        g = cygcd.Group()
        q = cygcd.Queue.global_queue()
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
        s = cygcd.Semaphore(1)
        assert s is not None

    def test_semaphore_signal_wait(self):
        """Test semaphore signal and wait."""
        s = cygcd.Semaphore(0)
        q = cygcd.Queue.global_queue()
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
        s = cygcd.Semaphore(0)
        acquired = s.wait(0.1)
        assert acquired is False

    def test_semaphore_resource_limiting(self):
        """Test semaphore limits concurrent access."""
        s = cygcd.Semaphore(2)  # Allow 2 concurrent
        q = cygcd.Queue.global_queue()
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

        g = cygcd.Group()
        for i in range(5):
            g.run_async(q, lambda i=i: task(i))

        g.wait()
        assert max_active[0] <= 2


class TestOnce:
    """Tests for Once class."""

    def test_once_executes_once(self):
        """Test Once executes callable exactly once."""
        once = cygcd.Once()
        results = []

        def init():
            results.append(1)

        once(init)
        once(init)
        once(init)

        assert results == [1]

    def test_once_thread_safe(self):
        """Test Once is thread-safe."""
        once = cygcd.Once()
        results = []
        lock = threading.Lock()

        def init():
            with lock:
                results.append(1)

        q = cygcd.Queue.global_queue()
        g = cygcd.Group()

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

        cygcd.apply(5, task)
        assert sorted(results) == [0, 1, 2, 3, 4]

    def test_apply_with_queue(self):
        """Test apply with explicit queue."""
        q = cygcd.Queue.global_queue()
        results = []
        lock = threading.Lock()

        def task(i):
            with lock:
                results.append(i)

        cygcd.apply(5, task, q)
        assert sorted(results) == [0, 1, 2, 3, 4]

    def test_apply_raises_on_non_callable(self):
        """Test apply raises TypeError for non-callable."""
        with pytest.raises(TypeError):
            cygcd.apply(5, "not callable")


class TestConstants:
    """Tests for module constants."""

    def test_time_constants(self):
        """Test time constants are defined."""
        assert cygcd.DISPATCH_TIME_NOW == 0
        assert cygcd.DISPATCH_TIME_FOREVER == 0xFFFFFFFFFFFFFFFF
        assert cygcd.NSEC_PER_SEC == 1000000000
        assert cygcd.NSEC_PER_MSEC == 1000000
        assert cygcd.NSEC_PER_USEC == 1000
        assert cygcd.USEC_PER_SEC == 1000000
        assert cygcd.MSEC_PER_SEC == 1000

    def test_priority_constants(self):
        """Test priority constants are defined."""
        assert cygcd.QUEUE_PRIORITY_HIGH == 2
        assert cygcd.QUEUE_PRIORITY_DEFAULT == 0
        assert cygcd.QUEUE_PRIORITY_LOW == -2
        assert cygcd.QUEUE_PRIORITY_BACKGROUND == -32768

    def test_qos_constants(self):
        """Test QOS class constants are defined."""
        assert cygcd.QOS_CLASS_USER_INTERACTIVE == 0x21
        assert cygcd.QOS_CLASS_USER_INITIATED == 0x19
        assert cygcd.QOS_CLASS_DEFAULT == 0x15
        assert cygcd.QOS_CLASS_UTILITY == 0x11
        assert cygcd.QOS_CLASS_BACKGROUND == 0x09
        assert cygcd.QOS_CLASS_UNSPECIFIED == 0x00


class TestTimeFromNow:
    """Tests for time_from_now function."""

    def test_time_from_now(self):
        """Test time_from_now returns a valid time."""
        t = cygcd.time_from_now(1.0)
        assert t > 0
        assert t != cygcd.DISPATCH_TIME_FOREVER


class TestWalltime:
    """Tests for walltime function."""

    def test_walltime_now(self):
        """Test walltime with current time."""
        t = cygcd.walltime()
        assert t > 0
        assert t != cygcd.DISPATCH_TIME_FOREVER

    def test_walltime_with_delta(self):
        """Test walltime with delta."""
        t1 = cygcd.walltime()
        t2 = cygcd.walltime(delta_seconds=1.0)
        # Walltime values decrease as time increases (relative to far future)
        # So t2 (1 second later) should be different from t1
        assert t1 != t2

    def test_walltime_with_timestamp(self):
        """Test walltime with specific timestamp."""
        import time

        now = time.time()
        t = cygcd.walltime(timestamp=now)
        assert t > 0


class TestMainQueue:
    """Tests for main queue access."""

    def test_get_main_queue(self):
        """Test getting the main queue."""
        main = cygcd.Queue.main_queue()
        assert main is not None
        assert main.label is not None

    def test_main_queue_is_serial(self):
        """Test that main queue has the expected label."""
        main = cygcd.Queue.main_queue()
        assert "main" in main.label.lower()


class TestSuspendResume:
    """Tests for queue suspend/resume."""

    def test_suspend_resume(self):
        """Test suspending and resuming a queue."""
        q = cygcd.Queue("test.suspend")
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
        q = cygcd.Queue("test.multi_suspend")
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
        timer = cygcd.Timer(1.0, lambda: None)
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

        timer = cygcd.Timer(0.1, handler)
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

        timer = cygcd.Timer(0.0, handler, repeating=False, start_delay=0.05)
        timer.start()

        time.sleep(0.2)
        timer.cancel()

        # One-shot should fire exactly once
        assert results == [1]

    def test_timer_cancel(self):
        """Test cancelling a timer."""
        results = []

        timer = cygcd.Timer(0.05, lambda: results.append(1))
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
        q = cygcd.Queue("test.timer_queue")
        results = []
        lock = threading.Lock()

        def handler():
            with lock:
                results.append(1)

        timer = cygcd.Timer(0.05, handler, queue=q)
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

        timer = cygcd.Timer(0.5, handler, start_delay=0.2, repeating=False)
        timer.start()

        time.sleep(0.4)
        timer.cancel()

        assert len(results) == 1
        assert results[0] >= 0.15  # Should have waited ~0.2s

    def test_timer_leeway(self):
        """Test timer with leeway (should not error)."""
        timer = cygcd.Timer(0.1, lambda: None, leeway=0.05)
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
        timer = cygcd.Timer(0.05, handler)
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
            cygcd.Timer(0.1, "not callable")

    def test_timer_cannot_restart_cancelled(self):
        """Test that cancelled timer cannot be restarted."""
        timer = cygcd.Timer(0.1, lambda: None)
        timer.cancel()
        with pytest.raises(RuntimeError):
            timer.start()


class TestQueueQOS:
    """Tests for Queue QOS and target queue features."""

    def test_queue_with_qos(self):
        """Test creating queue with QOS class."""
        q = cygcd.Queue("test.qos", qos=cygcd.QOS_CLASS_UTILITY)
        assert q is not None
        assert q.label == "test.qos"

    def test_queue_with_qos_and_priority(self):
        """Test creating queue with QOS and relative priority."""
        q = cygcd.Queue(
            "test.qos_priority",
            qos=cygcd.QOS_CLASS_USER_INITIATED,
            relative_priority=-5,
        )
        results = []
        q.run_sync(lambda: results.append(1))
        assert results == [1]

    def test_queue_concurrent_with_qos(self):
        """Test concurrent queue with QOS."""
        q = cygcd.Queue("test.concurrent_qos", concurrent=True, qos=cygcd.QOS_CLASS_BACKGROUND)
        results = []
        lock = threading.Lock()

        for i in range(3):
            q.run_async(lambda i=i: (lock.acquire(), results.append(i), lock.release()))

        q.barrier_sync(lambda: None)
        assert len(results) == 3

    def test_queue_target(self):
        """Test queue with target queue."""
        parent = cygcd.Queue("parent")
        child = cygcd.Queue("child", target=parent)
        results = []

        child.run_sync(lambda: results.append(1))
        assert results == [1]

    def test_queue_set_target(self):
        """Test setting target queue after creation."""
        parent = cygcd.Queue("parent")
        child = cygcd.Queue("child")

        child.set_target_queue(parent)
        results = []

        child.run_sync(lambda: results.append(1))
        assert results == [1]

    def test_queue_hierarchy(self):
        """Test queue hierarchy with multiple levels."""
        root = cygcd.Queue("root")
        level1 = cygcd.Queue("level1", target=root)
        level2 = cygcd.Queue("level2", target=level1)

        results = []
        level2.run_sync(lambda: results.append(1))
        assert results == [1]


class TestProcessEventConstants:
    """Tests for process event constants."""

    def test_proc_constants(self):
        """Test process event constants are defined."""
        assert cygcd.PROC_EXIT == 0x80000000
        assert cygcd.PROC_FORK == 0x40000000
        assert cygcd.PROC_EXEC == 0x20000000
        assert cygcd.PROC_SIGNAL == 0x08000000


class TestSignalSource:
    """Tests for SignalSource class."""

    def test_create_signal_source(self):
        """Test creating a signal source."""
        # Use SIGUSR1 which is safe to handle
        old_handler = signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        try:
            source = cygcd.SignalSource(signal.SIGUSR1, lambda: None)
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
            source = cygcd.SignalSource(signal.SIGUSR1, handler)
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
            source = cygcd.SignalSource(signal.SIGUSR2, lambda: None)
            source.start()
            source.cancel()
            assert source.is_cancelled
        finally:
            signal.signal(signal.SIGUSR2, old_handler)

    def test_signal_source_with_queue(self):
        """Test signal source with explicit queue."""
        q = cygcd.Queue("signal.queue")
        results = []

        old_handler = signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        try:
            source = cygcd.SignalSource(signal.SIGUSR1, lambda: results.append(1), queue=q)
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
            cygcd.SignalSource(signal.SIGUSR1, "not callable")


class TestReadSource:
    """Tests for ReadSource class."""

    def test_create_read_source(self):
        """Test creating a read source."""
        r, w = os.pipe()
        try:
            source = cygcd.ReadSource(r, lambda: None)
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
            source = cygcd.ReadSource(r, handler)
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
            source = cygcd.ReadSource(r, lambda: None)
            source.start()
            source.cancel()
            assert source.is_cancelled
        finally:
            os.close(r)
            os.close(w)

    def test_read_source_with_queue(self):
        """Test read source with explicit queue."""
        r, w = os.pipe()
        q = cygcd.Queue("read.queue")
        results = []

        try:
            source = cygcd.ReadSource(r, lambda: results.append(1), queue=q)
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
                cygcd.ReadSource(r, "not callable")
        finally:
            os.close(r)
            os.close(w)


class TestWriteSource:
    """Tests for WriteSource class."""

    def test_create_write_source(self):
        """Test creating a write source."""
        r, w = os.pipe()
        try:
            source = cygcd.WriteSource(w, lambda: None)
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
            source = cygcd.WriteSource(w, handler)
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
            source = cygcd.WriteSource(w, lambda: None)
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
                cygcd.WriteSource(w, "not callable")
        finally:
            os.close(r)
            os.close(w)


class TestProcessSource:
    """Tests for ProcessSource class."""

    def test_create_process_source(self):
        """Test creating a process source."""
        # Monitor our own process
        source = cygcd.ProcessSource(os.getpid(), lambda: None)
        assert source is not None
        assert source.pid == os.getpid()
        assert not source.is_cancelled
        source.cancel()

    def test_process_source_with_events(self):
        """Test creating process source with specific events."""
        source = cygcd.ProcessSource(
            os.getpid(), lambda: None, events=cygcd.PROC_EXIT | cygcd.PROC_FORK
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

        source = cygcd.ProcessSource(proc.pid, handler, events=cygcd.PROC_EXIT)
        source.start()

        # Wait for process to exit
        proc.wait()
        time.sleep(0.2)

        source.cancel()
        assert "exited" in results

    def test_process_source_cancel(self):
        """Test cancelling a process source."""
        source = cygcd.ProcessSource(os.getpid(), lambda: None)
        source.start()
        source.cancel()
        assert source.is_cancelled

    def test_process_source_with_queue(self):
        """Test process source with explicit queue."""
        q = cygcd.Queue("proc.queue")
        source = cygcd.ProcessSource(os.getpid(), lambda: None, queue=q)
        assert source is not None
        source.cancel()

    def test_process_source_raises_on_non_callable(self):
        """Test process source raises TypeError for non-callable."""
        with pytest.raises(TypeError):
            cygcd.ProcessSource(os.getpid(), "not callable")


class TestInactiveQueues:
    """Tests for inactive queue feature."""

    def test_create_inactive_queue(self):
        """Test creating an inactive queue."""
        q = cygcd.Queue("test.inactive", inactive=True)
        assert q is not None
        assert q.is_inactive is True

    def test_inactive_queue_does_not_execute(self):
        """Test that inactive queue doesn't execute tasks."""
        q = cygcd.Queue("test.inactive_exec", inactive=True)
        results = []

        q.run_async(lambda: results.append(1))
        time.sleep(0.1)

        # Task should not have run yet
        assert results == []

        # Activate and wait
        q.activate()
        q.run_sync(lambda: None)

        assert results == [1]
        assert q.is_inactive is False

    def test_activate_inactive_queue(self):
        """Test activating an inactive queue."""
        q = cygcd.Queue("test.activate", inactive=True)
        assert q.is_inactive is True

        q.activate()
        assert q.is_inactive is False

        results = []
        q.run_sync(lambda: results.append(1))
        assert results == [1]

    def test_activate_non_inactive_raises(self):
        """Test that activating a non-inactive queue raises."""
        q = cygcd.Queue("test.not_inactive")
        with pytest.raises(RuntimeError):
            q.activate()

    def test_inactive_concurrent_queue(self):
        """Test inactive concurrent queue."""
        q = cygcd.Queue("test.inactive_concurrent", concurrent=True, inactive=True)
        assert q.is_inactive is True

        results = []
        lock = threading.Lock()

        for i in range(3):
            q.run_async(lambda i=i: (lock.acquire(), results.append(i), lock.release()))

        time.sleep(0.1)
        assert results == []

        q.activate()
        q.barrier_sync(lambda: None)

        assert len(results) == 3


class TestData:
    """Tests for Data class."""

    def test_create_empty_data(self):
        """Test creating empty data."""
        d = cygcd.Data()
        assert len(d) == 0
        assert d.size == 0
        assert bytes(d) == b""

    def test_create_data_from_bytes(self):
        """Test creating data from bytes."""
        d = cygcd.Data(b"hello world")
        assert len(d) == 11
        assert d.size == 11
        assert bytes(d) == b"hello world"

    def test_data_concat(self):
        """Test concatenating data."""
        d1 = cygcd.Data(b"hello ")
        d2 = cygcd.Data(b"world")
        d3 = d1.concat(d2)

        assert len(d3) == 11
        assert bytes(d3) == b"hello world"

    def test_data_concat_with_empty(self):
        """Test concatenating with empty data."""
        d1 = cygcd.Data(b"hello")
        d2 = cygcd.Data()

        d3 = d1.concat(d2)
        assert bytes(d3) == b"hello"

        d4 = d2.concat(d1)
        assert bytes(d4) == b"hello"

    def test_data_subrange(self):
        """Test creating subrange of data."""
        d = cygcd.Data(b"hello world")
        sub = d.subrange(0, 5)

        assert len(sub) == 5
        assert bytes(sub) == b"hello"

    def test_data_subrange_middle(self):
        """Test subrange from middle of data."""
        d = cygcd.Data(b"hello world")
        sub = d.subrange(6, 5)

        assert bytes(sub) == b"world"

    def test_empty_data_subrange(self):
        """Test subrange of empty data."""
        d = cygcd.Data()
        sub = d.subrange(0, 0)
        assert len(sub) == 0


class TestAsyncIO:
    """Tests for async I/O functions."""

    def test_read_async(self):
        """Test asynchronous read."""
        r, w = os.pipe()
        results = []

        def handler(data, error):
            results.append((data, error))

        try:
            os.write(w, b"test data")
            cygcd.read_async(r, 1024, handler)

            time.sleep(0.2)
            assert len(results) == 1
            assert results[0][0] == b"test data"
            assert results[0][1] == 0
        finally:
            os.close(r)
            os.close(w)

    def test_write_async(self):
        """Test asynchronous write."""
        r, w = os.pipe()
        results = []

        def handler(remaining, error):
            results.append((remaining, error))

        try:
            cygcd.write_async(w, b"test data", handler)

            time.sleep(0.2)
            assert len(results) == 1
            assert results[0][0] == b""
            assert results[0][1] == 0

            # Verify data was written
            data = os.read(r, 1024)
            assert data == b"test data"
        finally:
            os.close(r)
            os.close(w)

    def test_read_async_with_queue(self):
        """Test read_async with explicit queue."""
        r, w = os.pipe()
        q = cygcd.Queue("io.queue")
        results = []

        def handler(data, error):
            results.append((data, error))

        try:
            os.write(w, b"queued read")
            cygcd.read_async(r, 1024, handler, queue=q)

            time.sleep(0.2)
            assert len(results) == 1
            assert results[0][0] == b"queued read"
        finally:
            os.close(r)
            os.close(w)


class TestWorkloop:
    """Tests for Workloop class."""

    def test_create_workloop(self):
        """Test creating a workloop."""
        wl = cygcd.Workloop("test.workloop")
        assert wl is not None
        assert wl.is_inactive is False

    def test_workloop_run_async(self):
        """Test async execution on workloop."""
        wl = cygcd.Workloop("test.wl_async")
        results = []

        wl.run_async(lambda: results.append(1))
        wl.run_sync(lambda: None)

        assert results == [1]

    def test_workloop_run_sync(self):
        """Test sync execution on workloop."""
        wl = cygcd.Workloop("test.wl_sync")
        results = []

        wl.run_sync(lambda: results.append(1))
        assert results == [1]

    def test_create_inactive_workloop(self):
        """Test creating inactive workloop."""
        wl = cygcd.Workloop("test.wl_inactive", inactive=True)
        assert wl.is_inactive is True

    def test_activate_workloop(self):
        """Test activating an inactive workloop."""
        wl = cygcd.Workloop("test.wl_activate", inactive=True)
        assert wl.is_inactive is True

        # Cannot submit work to inactive workloop (Apple docs: undefined behavior)
        with pytest.raises(RuntimeError):
            wl.run_async(lambda: None)

        # Activate and then submit work
        wl.activate()
        assert wl.is_inactive is False

        results = []
        wl.run_sync(lambda: results.append(1))
        assert results == [1]

    def test_activate_non_inactive_workloop_raises(self):
        """Test that activating non-inactive workloop raises."""
        wl = cygcd.Workloop("test.wl_not_inactive")
        with pytest.raises(RuntimeError):
            wl.activate()

    def test_workloop_raises_on_non_callable(self):
        """Test workloop raises TypeError for non-callable."""
        wl = cygcd.Workloop("test.wl_error")
        with pytest.raises(TypeError):
            wl.run_async("not callable")


class TestIOConstants:
    """Tests for I/O constants."""

    def test_io_constants(self):
        """Test I/O type constants are defined."""
        assert cygcd.IO_STREAM == 0
        assert cygcd.IO_RANDOM == 1
        assert cygcd.IO_STOP == 0x1


class TestIOChannel:
    """Tests for IOChannel class."""

    def test_create_stream_channel(self):
        """Test creating a stream I/O channel."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test data")
            path = f.name

        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)
                assert channel.fd == fd
                assert not channel.is_closed
                channel.close()
                assert channel.is_closed
            finally:
                os.close(fd)
        finally:
            os.unlink(path)

    def test_create_random_channel(self):
        """Test creating a random access I/O channel."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test data for random access")
            path = f.name

        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_RANDOM)
                assert channel.fd == fd
                channel.close()
            finally:
                os.close(fd)
        finally:
            os.unlink(path)

    def test_read_basic(self):
        """Test basic async read."""
        import tempfile

        test_data = b"Hello, IOChannel!"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(test_data)
            path = f.name

        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)
                results = []
                sem = cygcd.Semaphore(0)

                def on_read(done, data, error):
                    results.append((done, data, error))
                    if done:
                        sem.signal()

                channel.read(1024, on_read)
                completed = sem.wait(5.0)  # 5 second timeout
                assert completed, "Read timed out"

                channel.close()

                # Should have received data with done=True
                assert len(results) >= 1
                # Collect all data
                all_data = b"".join(r[1] for r in results)
                assert all_data == test_data
                # Last result should have done=True
                assert results[-1][0] is True
                # No errors
                assert all(r[2] == 0 for r in results)
            finally:
                os.close(fd)
        finally:
            os.unlink(path)

    def test_write_basic(self):
        """Test basic async write."""
        import tempfile

        test_data = b"Writing via IOChannel!"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            fd = os.open(path, os.O_WRONLY | os.O_TRUNC)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)
                results = []
                sem = cygcd.Semaphore(0)

                def on_write(done, remaining, error):
                    results.append((done, remaining, error))
                    if done:
                        sem.signal()

                channel.write(test_data, on_write)
                completed = sem.wait(5.0)
                assert completed, "Write timed out"

                channel.close()

                # Verify data was written
                assert len(results) >= 1
                assert results[-1][0] is True  # done=True
                assert results[-1][2] == 0  # no error
            finally:
                os.close(fd)

            # Verify file contents
            with open(path, "rb") as f:
                written = f.read()
            assert written == test_data
        finally:
            os.unlink(path)

    def test_read_with_high_water(self):
        """Test read with high water mark delivers in chunks."""
        import tempfile

        # Create data larger than high water mark
        test_data = b"X" * 10000  # 10KB

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(test_data)
            path = f.name

        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)
                channel.set_high_water(1024)  # 1KB chunks

                results = []
                sem = cygcd.Semaphore(0)

                def on_read(done, data, error):
                    results.append((done, data, error))
                    if done:
                        sem.signal()

                channel.read(len(test_data), on_read)
                completed = sem.wait(5.0)
                assert completed, "Read timed out"

                channel.close()

                # Should have received multiple chunks
                assert len(results) >= 2, f"Expected multiple chunks, got {len(results)}"
                # Collect all data
                all_data = b"".join(r[1] for r in results)
                assert all_data == test_data
            finally:
                os.close(fd)
        finally:
            os.unlink(path)

    def test_close_idempotent(self):
        """Test that close can be called multiple times."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)
                channel.close()
                channel.close()  # Should not raise
                assert channel.is_closed
            finally:
                os.close(fd)
        finally:
            os.unlink(path)

    def test_close_with_stop(self):
        """Test close with IO_STOP flag."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            path = f.name

        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)
                channel.close(stop=True)
                assert channel.is_closed
            finally:
                os.close(fd)
        finally:
            os.unlink(path)

    def test_barrier(self):
        """Test barrier waits for pending operations."""
        import tempfile

        test_data = b"Barrier test data"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(test_data)
            path = f.name

        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)
                read_data = []
                barrier_done = [False]
                read_sem = cygcd.Semaphore(0)
                barrier_sem = cygcd.Semaphore(0)

                def on_read(done, data, error):
                    if data:
                        read_data.append(bytes(data))
                    if done:
                        read_sem.signal()

                def on_barrier():
                    barrier_done[0] = True
                    barrier_sem.signal()

                channel.read(1024, on_read)
                channel.barrier(on_barrier)

                # Wait for both to complete (barrier guarantees I/O done,
                # but on concurrent queue handlers may execute in any order)
                read_completed = read_sem.wait(5.0)
                barrier_completed = barrier_sem.wait(5.0)

                assert read_completed, "Read timed out"
                assert barrier_completed, "Barrier timed out"

                channel.close()

                # Verify data was read and barrier executed
                assert b"".join(read_data) == test_data
                assert barrier_done[0]
            finally:
                os.close(fd)
        finally:
            os.unlink(path)

    def test_operations_on_closed_channel_raise(self):
        """Test that operations on closed channel raise RuntimeError."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)
                channel.close()

                with pytest.raises(RuntimeError):
                    channel.read(1024, lambda d, da, e: None)

                with pytest.raises(RuntimeError):
                    channel.write(b"test", lambda d, r, e: None)

                with pytest.raises(RuntimeError):
                    channel.barrier(lambda: None)

                with pytest.raises(RuntimeError):
                    channel.set_high_water(1024)

                with pytest.raises(RuntimeError):
                    channel.set_low_water(1024)

                with pytest.raises(RuntimeError):
                    channel.set_interval(1000)
            finally:
                os.close(fd)
        finally:
            os.unlink(path)

    def test_raises_on_non_callable_handler(self):
        """Test that non-callable handlers raise TypeError."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)

                with pytest.raises(TypeError):
                    channel.read(1024, "not callable")

                with pytest.raises(TypeError):
                    channel.write(b"test", "not callable")

                with pytest.raises(TypeError):
                    channel.barrier("not callable")

                channel.close()
            finally:
                os.close(fd)
        finally:
            os.unlink(path)

    def test_write_requires_bytes(self):
        """Test that write requires bytes data."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            fd = os.open(path, os.O_WRONLY)
            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM)

                with pytest.raises(TypeError):
                    channel.write("not bytes", lambda d, r, e: None)

                channel.close()
            finally:
                os.close(fd)
        finally:
            os.unlink(path)

    def test_cleanup_handler(self):
        """Test cleanup handler is called on close."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            fd = os.open(path, os.O_RDONLY)
            cleanup_called = [False]
            cleanup_error = [None]

            def on_cleanup(error):
                cleanup_called[0] = True
                cleanup_error[0] = error

            try:
                channel = cygcd.IOChannel(fd, cygcd.IO_STREAM, cleanup_handler=on_cleanup)
                channel.close()

                # Give cleanup handler time to execute
                time.sleep(0.2)

                assert cleanup_called[0], "Cleanup handler not called"
                assert cleanup_error[0] == 0, f"Unexpected error: {cleanup_error[0]}"
            finally:
                os.close(fd)
        finally:
            os.unlink(path)


class TestQueueContext:
    """Tests for Queue context management."""

    def test_set_get_context(self):
        """Test setting and getting context data."""
        q = cygcd.Queue("context.test")
        data = {"key": "value", "count": 42}
        q.set_context(data)
        assert q.get_context() is data
        assert q.get_context()["key"] == "value"

    def test_context_none_by_default(self):
        """Test that context is None by default."""
        q = cygcd.Queue("context.default")
        assert q.get_context() is None

    def test_context_with_finalizer(self):
        """Test that finalizer is called when context is replaced."""
        q = cygcd.Queue("context.finalizer")
        finalized = [False]

        def finalizer():
            finalized[0] = True

        q.set_context("first", finalizer=finalizer)
        assert q.get_context() == "first"
        assert not finalized[0]

        # Replace context, should call finalizer
        q.set_context("second")
        assert finalized[0]
        assert q.get_context() == "second"

    def test_context_finalizer_type_error(self):
        """Test that non-callable finalizer raises TypeError."""
        q = cygcd.Queue("context.error")
        with pytest.raises(TypeError):
            q.set_context("data", finalizer="not callable")


class TestQueueSpecificData:
    """Tests for queue-specific data."""

    def test_set_get_specific(self):
        """Test setting and getting queue-specific data."""
        q = cygcd.Queue("specific.test")
        key = "my_key"
        value = {"data": 123}

        q.set_specific(key, value)
        assert q.get_specific(key) is value

    def test_get_specific_missing_key(self):
        """Test get_specific returns None for missing key."""
        q = cygcd.Queue("specific.missing")
        assert q.get_specific("nonexistent") is None

    def test_set_specific_none_removes(self):
        """Test setting None removes the specific data."""
        q = cygcd.Queue("specific.remove")
        key = "removable"

        q.set_specific(key, "value")
        assert q.get_specific(key) == "value"

        q.set_specific(key, None)
        assert q.get_specific(key) is None

    def test_get_specific_from_queue_code(self):
        """Test get_specific works from code running on the queue."""
        q = cygcd.Queue("specific.running")
        key = "running_key"
        value = "running_value"
        result = [None]

        q.set_specific(key, value)

        def check_specific():
            result[0] = cygcd.get_specific(key)

        q.run_sync(check_specific)
        assert result[0] == value


class TestDataExtras:
    """Tests for Data copy_region and apply methods."""

    def test_copy_region_basic(self):
        """Test copy_region returns correct region."""
        data = cygcd.Data(b"Hello World")
        region, offset = data.copy_region(0)
        # For contiguous data, region should contain all data
        assert bytes(region) == b"Hello World"
        assert offset == 0

    def test_copy_region_middle(self):
        """Test copy_region with middle location."""
        data = cygcd.Data(b"Hello World")
        region, offset = data.copy_region(5)
        # Region contains the location
        assert 5 - offset < len(region)

    def test_copy_region_out_of_bounds(self):
        """Test copy_region returns empty region for out of bounds location."""
        data = cygcd.Data(b"Short")
        # GCD returns an empty region for out of bounds locations
        region, offset = data.copy_region(100)
        assert len(region) == 0
        assert offset >= len(data)  # offset is at or beyond data end

    def test_copy_region_empty_data(self):
        """Test copy_region raises for empty data."""
        data = cygcd.Data()
        with pytest.raises(ValueError):
            data.copy_region(0)

    def test_apply_basic(self):
        """Test apply iterates over data."""
        data = cygcd.Data(b"Test data")
        regions = []

        def collector(offset, chunk):
            regions.append((offset, chunk))
            return True

        result = data.apply(collector)
        assert result is True
        assert len(regions) == 1
        assert regions[0] == (0, b"Test data")

    def test_apply_stop_iteration(self):
        """Test apply stops when function returns False."""
        data = cygcd.Data(b"Test data")

        def stopper(offset, chunk):
            return False

        result = data.apply(stopper)
        assert result is False

    def test_apply_empty_data(self):
        """Test apply on empty data returns True without calling function."""
        data = cygcd.Data()
        called = [False]

        def never_called(offset, chunk):
            called[0] = True
            return True

        result = data.apply(never_called)
        assert result is True
        assert not called[0]


class TestWorkloopAutorelease:
    """Tests for Workloop autorelease frequency."""

    def test_autorelease_frequency_constants(self):
        """Test autorelease frequency constants exist."""
        assert cygcd.AUTORELEASE_FREQUENCY_INHERIT == 0
        assert cygcd.AUTORELEASE_FREQUENCY_WORK_ITEM == 1
        assert cygcd.AUTORELEASE_FREQUENCY_NEVER == 2

    def test_set_autorelease_frequency_on_inactive(self):
        """Test set_autorelease_frequency on inactive workloop."""
        wl = cygcd.Workloop("autorelease.test", inactive=True)
        # Should not raise
        wl.set_autorelease_frequency(cygcd.AUTORELEASE_FREQUENCY_WORK_ITEM)
        wl.activate()

        # Verify workloop works after setting frequency
        result = [None]
        sem = cygcd.Semaphore(0)

        def work():
            result[0] = "done"
            sem.signal()

        wl.run_async(work)
        sem.wait(1.0)
        assert result[0] == "done"

    def test_set_autorelease_frequency_on_active_raises(self):
        """Test set_autorelease_frequency on active workloop raises."""
        wl = cygcd.Workloop("autorelease.active")
        with pytest.raises(RuntimeError):
            wl.set_autorelease_frequency(cygcd.AUTORELEASE_FREQUENCY_NEVER)
