"""FastAPI local recovery never touches cloud or external healthy instances."""
from __future__ import annotations

from types import SimpleNamespace
import pytest

from apps.desktop.backend_recovery import BackendRecoverySupervisor


def test_no_recovery_for_external_service():
    calls = []
    monitor = BackendRecoverySupervisor(
        process=lambda: None,
        restart=lambda: calls.append("restart"),
        healthy=lambda: True,
    )
    monitor.start()
    assert monitor.check_once() == "external"
    monitor.stop()
    assert calls == []


def test_restart_crashed_owned_process(monkeypatch):
    import apps.desktop.backend_recovery as recovery
    clock = [100.0]
    monkeypatch.setattr(recovery.time, "monotonic", lambda: clock[0])
    current = [SimpleNamespace(poll=lambda: 12)]
    calls = []

    def restart():
        calls.append("restart")
        current[0] = SimpleNamespace(poll=lambda: None)
        return current[0]

    monitor = BackendRecoverySupervisor(
        process=lambda: current[0],
        restart=restart,
        healthy=lambda: bool(calls),
        poll_seconds=1,
    )
    assert monitor.check_once() == "recovered"
    assert calls == ["restart"]
    assert monitor.check_once() == "running"


def test_crashes_are_bounded_with_backoff(monkeypatch):
    import apps.desktop.backend_recovery as recovery
    now = [100.0]
    monkeypatch.setattr(recovery.time, "monotonic", lambda: now[0])
    dead = SimpleNamespace(poll=lambda: 1)
    count = []

    def failing_restart():
        count.append(1)
        raise OSError("backend unavailable")

    monitor = BackendRecoverySupervisor(
        process=lambda: dead, restart=failing_restart,
        healthy=lambda: False, poll_seconds=1.0, max_restarts=2,
    )
    assert monitor.check_once() == "failed"
    assert monitor.check_once() == "backoff"
    now[0] += 2
    assert monitor.check_once() == "failed"
    now[0] += 4
    assert monitor.check_once() == "exhausted"
    assert monitor.check_once() == "stopped"
    assert len(count) == 2


def test_shutdown_disables_recovery():
    calls = []
    dead = SimpleNamespace(poll=lambda: 1)
    monitor = BackendRecoverySupervisor(
        process=lambda: dead,
        restart=lambda: calls.append(1),
        healthy=lambda: False,
    )
    monitor.stop()
    assert monitor.check_once() == "stopped"
    assert not calls


def test_healthy_external_backend_prevents_duplicate_start():
    calls = []
    dead = SimpleNamespace(poll=lambda: 1)
    monitor = BackendRecoverySupervisor(
        process=lambda: dead,
        restart=lambda: calls.append(1),
        healthy=lambda: True,
    )
    assert monitor.check_once() == "external"
    assert calls == []


def test_invalid_config_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        BackendRecoverySupervisor(
            process=lambda: None,
            restart=lambda: None,
            healthy=lambda: False,
            poll_seconds=0,
        )


def test_expired_attempt_window_allows_future_recovery(monkeypatch):
    import apps.desktop.backend_recovery as recovery
    time_source = [100.0]
    monkeypatch.setattr(recovery.time, "monotonic", lambda: time_source[0])
    dead = SimpleNamespace(poll=lambda: 1)
    restart_calls = []
    monitor = BackendRecoverySupervisor(
        process=lambda: dead,
        restart=lambda: restart_calls.append(1),
        healthy=lambda: False,
        poll_seconds=1, max_restarts=1, window_seconds=10,
    )
    assert monitor.check_once() == "failed"
    time_source[0] += 12
    assert monitor.check_once() == "failed"
    assert len(restart_calls) == 2


def test_owned_process_monitor_starts_and_stops_cleanly():
    own = SimpleNamespace(poll=lambda: None)
    monitor = BackendRecoverySupervisor(
        process=lambda: own,
        restart=lambda: (_ for _ in ()).throw(AssertionError("unexpected restart")),
        healthy=lambda: True,
        poll_seconds=0.01,
    )
    monitor.start()
    assert monitor._thread is not None
    monitor.stop()
    assert monitor.check_once() == "stopped"
    assert not monitor._thread.is_alive()


def test_initial_start_failure_can_recover_once(monkeypatch):
    import apps.desktop.backend_recovery as module
    monkeypatch.setattr(module.time, "monotonic", lambda: 300.0)
    running = [None]
    restarts = []

    def restart():
        restarts.append(1)
        running[0] = SimpleNamespace(poll=lambda: None)
        return running[0]

    supervisor = BackendRecoverySupervisor(
        process=lambda: running[0],
        restart=restart,
        healthy=lambda: bool(restarts),
        allow_initial_retry=True,
        poll_seconds=10,
    )
    assert supervisor.check_once() == "recovered"
    assert supervisor.check_once() == "running"
    assert restarts == [1]


def test_initial_failure_does_not_restart_healthy_unowned_api():
    starts = []
    monitor = BackendRecoverySupervisor(
        process=lambda: None,
        restart=lambda: starts.append(1),
        healthy=lambda: True,
        allow_initial_retry=True,
    )
    monitor.start()
    assert monitor.check_once() == "external"
    assert starts == []


def process(exit_code=None):
    return SimpleNamespace(poll=lambda: exit_code)


def test_recovery_never_claims_healthy_external_api():
    calls = []
    supervisor = BackendRecoverySupervisor(
        process=lambda: None, restart=lambda: calls.append("spawn"), healthy=lambda: True,
        allow_initial_retry=True,
    )
    assert supervisor.start() is False
    assert supervisor.check_once() == "external"
    assert calls == []


def test_initial_failure_retries_then_restores_owned_process(monkeypatch):
    import apps.desktop.backend_recovery as module
    monkeypatch.setattr(module.time, "monotonic", lambda: 100)
    owned = [None]
    attempts = []
    def restart():
        attempts.append(1)
        owned[0] = process()
        return owned[0]
    sup = BackendRecoverySupervisor(
        process=lambda: owned[0], restart=restart,
        healthy=lambda: bool(attempts), allow_initial_retry=True,
    )
    assert sup.check_once() == "recovered"
    assert sup.check_once() == "running"
    assert attempts == [1]


def test_crash_recovery_is_bounded_with_backoff(monkeypatch):
    import apps.desktop.backend_recovery as module
    clock = [100]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    calls = []
    def fail():
        calls.append(1)
        raise RuntimeError("backend crash")
    sup = BackendRecoverySupervisor(
        process=lambda: process(7), restart=fail, healthy=lambda: False,
        poll_seconds=1, max_restarts=2, window_seconds=120,
    )
    assert sup.check_once() == "failed"
    assert sup.check_once() == "backoff"
    clock[0] += 2
    assert sup.check_once() == "failed"
    clock[0] += 4
    assert sup.check_once() == "exhausted"
    assert sup.check_once() == "stopped"
    assert len(calls) == 2


def test_attempt_window_expires(monkeypatch):
    import apps.desktop.backend_recovery as module
    clock = [100]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    calls = []
    sup = BackendRecoverySupervisor(
        process=lambda: process(1), restart=lambda: calls.append(1),
        healthy=lambda: False, poll_seconds=1,
        max_restarts=1, window_seconds=10,
    )
    assert sup.check_once() == "failed"
    clock[0] += 12
    assert sup.check_once() == "failed"
    assert calls == [1, 1]


def test_stop_disables_restart():
    calls = []
    sup = BackendRecoverySupervisor(
        process=lambda: process(1), restart=lambda: calls.append(1),
        healthy=lambda: False,
    )
    sup.stop()
    assert sup.check_once() == "stopped"
    assert calls == []


def test_running_owned_child_is_left_alone():
    calls = []
    sup = BackendRecoverySupervisor(
        process=lambda: process(), restart=lambda: calls.append(1),
        healthy=lambda: False,
    )
    assert sup.check_once() == "running"
    assert calls == []


def test_healthy_backend_after_crash_is_not_taken_over():
    calls = []
    sup = BackendRecoverySupervisor(
        process=lambda: process(0), restart=lambda: calls.append(1),
        healthy=lambda: True,
    )
    assert sup.check_once() == "external"
    assert calls == []


@pytest.mark.parametrize("kwargs", [
    {"poll_seconds": 0}, {"max_restarts": 0}, {"window_seconds": -2},
])
def test_invalid_configuration_rejected(kwargs):
    with pytest.raises(ValueError):
        BackendRecoverySupervisor(
            process=lambda: None, restart=lambda: None,
            healthy=lambda: False, **kwargs,
        )


def test_no_owned_process_no_initial_retry_means_no_thread():
    sup = BackendRecoverySupervisor(
        process=lambda: None, restart=lambda: None,
        healthy=lambda: False,
    )
    assert sup.start() is False
    assert sup._thread is None


def test_supervisor_thread_stops_on_user_shutdown():
    sup = BackendRecoverySupervisor(
        process=lambda: process(), restart=lambda: None,
        healthy=lambda: True, poll_seconds=0.01,
    )
    assert sup.start() is True
    sup.stop()
    assert sup._thread is not None
    assert not sup._thread.is_alive()
