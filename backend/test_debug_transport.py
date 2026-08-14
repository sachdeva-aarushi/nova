from backend.debug_transport import DebugTransport


def test_debug_transport_keeps_event_logs_bounded() -> None:
    transport = DebugTransport()
    transport.max_events = 3
    transport.max_broadcasts = 2
    transport.max_ws_messages = 2

    for i in range(10):
        transport.record_event({"n": i})
    for i in range(10):
        transport.record_broadcast({"n": i})
    for i in range(10):
        transport.record_ws_message({"n": i})

    assert len(transport._events_published) == 3
    assert len(transport._broadcasts) == 2
    assert len(transport._ws_messages) == 2
    assert list(transport._events_published)[0]["n"] == 7
    assert list(transport._broadcasts)[0]["n"] == 8
    assert list(transport._ws_messages)[0]["n"] == 8
