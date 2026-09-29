#!/usr/bin/env python3
"""ULPF cross-platform real-time connector — main entry point.

Usage:
    python connector.py                          # stream live, auto-detect
    python connector.py --once                   # read available now, exit
    python connector.py --skip-history           # ignore bookmarks, start at tail
    python connector.py --debug-events           # log every poll with cursor + count
    python connector.py --adapter windows_eventlog
    python connector.py --config /path/to.json
    python connector.py --log-level DEBUG
    python connector.py --dry-run                # print config + availability
    python connector.py --no-heartbeat           # disable heartbeat
    python connector.py --no-config-poll         # disable desired-state convergence
    python connector.py --wait-for-backend N     # wait up to N seconds for the
                                                 # backend before giving up
                                                 # (default: 300)

See README.md for configuration and service installation.

Startup behavior:
    When installed as a service (Windows Scheduled Task, systemd unit,
    launchd agent), the connector may start before the backend is up. In
    that case, this script will retry login with exponential backoff for
    up to --wait-for-backend seconds before giving up. This makes the
    "connector at boot, backend starts a bit later" flow work without
    needing external retry logic.
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ulpf_connector
from ulpf_connector.adapters import build_adapters
from ulpf_connector.core.client import UlpfClient
from ulpf_connector.core.config import load_config
from ulpf_connector.core.heartbeat import (
    HeartbeatThread, ConfigPollerThread, EventsCounter,
)
from ulpf_connector.core.lifecycle import AdapterLifecycleManager
from ulpf_connector.core.logging import setup_logging
from ulpf_connector.core.queue import SpoolQueue

log = logging.getLogger("connector")

_shutdown = threading.Event()


def _install_signal_handlers() -> None:
    def _handler(signum, frame):
        log.info("shutdown.signal signum=%d", signum)
        _shutdown.set()
    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def _wait_for_backend(client: UlpfClient, timeout_s: float) -> bool:
    """Try to authenticate, retrying until `timeout_s` elapses.

    Returns True on success, False on timeout. Respects _shutdown so the
    user can Ctrl+C during the wait.

    Backoff: 1s, 2s, 4s, 8s, 15s, then steady 15s. Total attempts depend
    on timeout_s but are bounded by the backoff cap.
    """
    if client.ensure_authenticated():
        return True

    log.info("connector.waiting_for_backend timeout_s=%d", int(timeout_s))
    deadline = time.time() + timeout_s
    delays = [1, 2, 3, 5]
    attempt = 0

    while time.time() < deadline and not _shutdown.is_set():
        delay = delays[min(attempt, len(delays) - 1)]
        _shutdown.wait(timeout=delay)
        if _shutdown.is_set():
            return False
        attempt += 1
        if client.ensure_authenticated():
            log.info("connector.backend_ready attempts=%d", attempt)
            return True
        remaining = max(0, int(deadline - time.time()))
        log.info("connector.backend_still_down attempts=%d remaining_s=%d",
                 attempt, remaining)

    return False


def _drain_worker(client: UlpfClient, queue: SpoolQueue, counter: EventsCounter) -> None:
    while not _shutdown.is_set():
        payload = queue.get_nowait()
        if payload is None:
            time.sleep(0.05)
            continue
        ok = client.send(payload)
        if ok:
            counter.incr()
            log.info(
                "drain.sent source_type=%s file=%s total=%d",
                payload.get("source_type"),
                payload.get("filename"),
                counter.total,
            )
        else:
            log.error("drain.dropped source_type=%s", payload.get("source_type"))


def run_stream(
    config,
    *,
    enable_heartbeat: bool = True,
    enable_config_poll: bool = True,
    skip_history: bool = False,
    debug_events: bool = False,
    wait_for_backend_s: float = 300.0,
) -> int:
    client = UlpfClient(config)

    # Wait for backend. Installed-as-a-service starts can race with the
    # backend coming up; this gives us time without crashing the task.
    if not _wait_for_backend(client, wait_for_backend_s):
        log.error("connector.backend_unreachable_after_s=%d", int(wait_for_backend_s))
        client.close()
        return 2

    # Override per-adapter config based on CLI flags.
    adapter_cfg = dict(config.adapters)
    for name, cfg in adapter_cfg.items():
        if isinstance(cfg, dict):
            override = dict(cfg)
            if skip_history:
                override["force_anchor_now"] = True
            if debug_events:
                override["debug_events"] = True
            adapter_cfg[name] = override
    if skip_history:
        log.info("connector.skip_history_forced adapters=%s", list(adapter_cfg))
    if debug_events:
        log.info("connector.debug_events_enabled adapters=%s", list(adapter_cfg))

    queue = SpoolQueue(config.queue.max_in_memory, config.queue.spool_file)
    if config.queue.spool_replay_on_start:
        n = queue.replay_spool()
        if n:
            log.info("connector.spool_replayed count=%d", n)

    counter = EventsCounter()

    lifecycle = AdapterLifecycleManager(
        queue=queue,
        on_event=lambda payload: (queue.put(payload), counter.incr()),
    )

    initial_adapters = build_adapters(adapter_cfg)
    for a in initial_adapters:
        lifecycle.start(a)

    if not lifecycle.running():
        log.error("connector.no_adapters_available")
        return 3

    log.info(
        "connector.started running=%s available=%s",
        lifecycle.running(), lifecycle.available(),
    )

    heartbeat: HeartbeatThread | None = None
    config_poller: ConfigPollerThread | None = None

    if enable_heartbeat:
        heartbeat = HeartbeatThread(
            base_url=config.ulpf_base,
            auth_header=client._auth_header,
            reauth_fn=lambda: client.ensure_authenticated(force=True),
            running_adapters_fn=lifecycle.running,
            available_adapters=lifecycle.available(),
            events_counter=counter,
            version=ulpf_connector.__version__,
        )
        heartbeat.start()
        log.info("connector.heartbeat_started id=%s", heartbeat.connector_id)

        if enable_config_poll:
            config_poller = ConfigPollerThread(
                heartbeat=heartbeat,
                lifecycle=lifecycle,
                default_interval_s=30.0,
            )
            config_poller.start()
            log.info("connector.config_poller_started interval=%ss", config_poller.interval_s)

    drain = threading.Thread(
        target=_drain_worker, args=(client, queue, counter),
        name="drain", daemon=True,
    )
    drain.start()

    try:
        while not _shutdown.is_set():
            _shutdown.wait(timeout=1.0)
    finally:
        log.info("connector.stopping")
        if config_poller is not None:
            config_poller.stop()
        lifecycle.stop_all(timeout=5.0)
        try:
            spilled = queue.spill_all()
            if spilled:
                log.info("connector.spilled_to_disk count=%d", spilled)
        except Exception:
            pass
        if heartbeat is not None:
            heartbeat.stop()
        client.close()

    return 0


def run_once(config, adapter_filter: str | None, limit: int,
             wait_for_backend_s: float = 60.0) -> int:
    client = UlpfClient(config)
    if not _wait_for_backend(client, wait_for_backend_s):
        log.error("connector.backend_unreachable_after_s=%d", int(wait_for_backend_s))
        client.close()
        return 2

    adapters = build_adapters(config.adapters)
    if adapter_filter:
        adapters = [a for a in adapters if a.name == adapter_filter]
        if not adapters:
            log.error("connector.adapter_not_found name=%s", adapter_filter)
            return 3
    if not adapters:
        log.error("connector.no_adapters_available")
        return 3

    counter = EventsCounter()
    total = 0
    ok = 0
    for a in adapters:
        log.info("once.reading adapter=%s limit=%d", a.name, limit)
        try:
            for event in a.read_once(limit=limit):
                total += 1
                if client.send(event.to_payload()):
                    ok += 1
                    counter.incr()
        except Exception as exc:
            log.error("once.adapter_failed name=%s err=%s", a.name, exc)

    try:
        hb = HeartbeatThread(
            base_url=config.ulpf_base,
            auth_header=client._auth_header,
            running_adapters_fn=lambda: [a.name for a in adapters],
            available_adapters=[a.name for a in adapters],
            events_counter=counter,
            version=ulpf_connector.__version__,
        )
        hb.send_once()
        log.info("heartbeat.once_sent id=%s", hb.connector_id)
    except Exception as exc:
        log.warning("heartbeat.once_failed err=%s", exc)

    log.info("once.done total=%d sent=%d", total, ok)
    client.close()
    return 0 if ok == total else 1


def print_dry_run(config) -> None:
    print(f"ULPF base:      {config.ulpf_base}")
    print(f"Auth email:     {config.auth.email}")
    print(f"Auth password:  {'<env>' if config.resolve_password() else '<missing>'}")
    print(f"Spool file:     {config.queue.spool_file}")
    print(f"Log level:      {config.log_level}")
    print()
    print("Adapter availability:")
    adapters = build_adapters(config.adapters)
    available_names = {a.name for a in adapters}
    from ulpf_connector.adapters import _all_adapter_classes
    for cls in _all_adapter_classes():
        mark = "ENABLED" if cls.name in available_names else "SKIPPED"
        print(f"  {mark:<8}  {cls.name}")


def main() -> int:
    ap = argparse.ArgumentParser(description="ULPF cross-platform connector")
    ap.add_argument("--config", help="Path to config JSON (default ~/.ulpf/connector.json)")
    ap.add_argument("--once", action="store_true", help="Read available now, then exit")
    ap.add_argument("--limit", type=int, default=100, help="Max events per adapter in --once mode")
    ap.add_argument("--adapter", help="Force a single adapter (e.g. linux_journald)")
    ap.add_argument("--dry-run", action="store_true", help="Print config + adapter availability, exit")
    ap.add_argument("--no-heartbeat", action="store_true", help="Disable heartbeat to backend")
    ap.add_argument("--no-config-poll", action="store_true", help="Disable desired-state convergence")
    ap.add_argument("--skip-history", action="store_true",
                    help="Ignore bookmarks; start at the current tail of every channel.")
    ap.add_argument("--debug-events", action="store_true",
                    help="Log every poll with cursor and count for each channel.")
    ap.add_argument("--wait-for-backend", type=int, default=3600,
                    help="Seconds to wait for the backend before giving up "
                         "(default: 300 for stream, 60 for --once).")
    ap.add_argument("--log-level", help="Override log level (DEBUG, INFO, WARNING, ERROR)")
    args = ap.parse_args()

    config = load_config(args.config)
    level = args.log_level or ("DEBUG" if args.debug_events else config.log_level)
    setup_logging(level, log_file=config.log_file)

    if args.dry_run:
        print_dry_run(config)
        return 0

    _install_signal_handlers()

    if args.once:
        # In --once mode, don't wait as long by default — this is a
        # "read and exit" invocation, not a long-running service.
        wait_s = args.wait_for_backend if args.wait_for_backend != 3600 else 60
        return run_once(config, args.adapter, args.limit, wait_for_backend_s=wait_s)
    return run_stream(
        config,
        enable_heartbeat=not args.no_heartbeat,
        enable_config_poll=not args.no_config_poll,
        skip_history=args.skip_history,
        debug_events=args.debug_events,
        wait_for_backend_s=float(args.wait_for_backend),
    )


if __name__ == "__main__":
    sys.exit(main())