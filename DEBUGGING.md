# NOVA Transport Chain Debugging Guide

## Overview

You reported two critical issues:

1. **Voice input not reaching backend agent** (Chain 2 issue)
2. **Data not updating in frontend from data simulator** (Chain 1 issue)

This document provides tools and strategies to diagnose and fix these transport/state synchronization problems.

---

## Architecture Overview

### Chain 1: Simulator → Frontend (Broken)
```
INTERNAL SIMULATOR (data_simulator/)
       ↓ publishes to "raw.telemetry"
EVENT BUS (backend/bus/event_bus.py)
       ↓ dispatch loop routes to subscribers
FACTORY STATE + WS BRIDGE (backend/api/ws_session.py)
       ↓ on_raw_telemetry() calls broadcast_all()
WEBSOCKET MANAGER (ConnectionManager)
       ↓ sends JSON to all connected clients
FRONTEND (useSessionSocket.ts)
       ↓ onMessage() handler
ZUSTAND STORE (useDemoStore.ts, useCaseStore.ts)
       ↓ updateSensor(), addTickerItem()
UI COMPONENTS
```

### Chain 2: Frontend Voice → Backend (Broken)
```
FRONTEND
   ↓ sends voice/text via WebSocket or HTTP
API ROUTE (routes_voice_command.py, routes_voice.py)
   ↓ receives text/audio
BACKEND AGENT (voice_agent.py, sensor_event_intelligence.py)
   ↓ processes through agents
EVENT BUS (publishes results)
   ↓
RESPONSE ORCHESTRATOR → FRONTEND
```

---

## Debugging Tools Available

### 1. **Debug Transport API** (`backend/debug_transport.py`)

Automatically enabled in development mode. Provides real-time visibility into:
- Event bus publications (all topics, all events)
- WebSocket broadcasts (all message types, all clients)
- Subscription counts and matches

#### Access Points

**GET `/api/debug/transport/state`**
```bash
curl http://localhost:8000/api/debug/transport/state | jq
```

Returns:
- Event bus status (running, queue size, subscriptions)
- WebSocket connection counts
- Event publication history
- Broadcast history by message type

**POST `/api/debug/transport/test`**
```bash
curl -X POST "http://localhost:8000/api/debug/transport/test?topic=raw.telemetry" | jq
```

Publishes a test event and returns:
- Event topic
- Number of matching subscribers
- Number of broadcasts triggered
- Recent events in the pipeline

**GET `/api/debug/subscriptions`**
```bash
curl http://localhost:8000/api/debug/subscriptions | jq
```

Shows all active subscriptions:
- Topics subscribed to
- Handler functions for each topic
- Total subscription count

**GET `/api/debug/ws/connections`**
```bash
curl http://localhost:8000/api/debug/ws/connections | jq
```

Shows WebSocket connection state:
- Number of sessions
- Clients per session
- Connection status

### 2. **Integration Test Suite** (`backend/test_transport_chain.py`)

Comprehensive end-to-end test of both chains. Requires backend running.

```bash
# In the nova project root:
python -m backend.test_transport_chain
```

Tests:
- ✅ Backend connectivity
- ✅ Event bus health (subscriptions, dispatch loop)
- ✅ Chain 1: Publishes test event → verifies WebSocket delivery
- ✅ Chain 2: Sends voice command → verifies agent processing

Output shows:
- Pass/fail for each chain
- Detailed error messages
- Message counts and types received
- WebSocket connection status

---

## How to Diagnose Chain 1 Breakage

### Symptom: Frontend Not Receiving Simulator Events

#### Step 1: Check Backend Health
```bash
curl http://localhost:8000/health
```
Expected: `{"status": "ok", "version": "1.0.0"}`

#### Step 2: Verify Event Bus is Running
```bash
curl http://localhost:8000/api/debug/transport/state | jq '.event_bus'
```
Expected:
- `running: true`
- `subscriptions > 0`
- `queue_size == 0` (should drain quickly)

#### Step 3: Verify WebSocket Subscriptions
```bash
curl http://localhost:8000/api/debug/subscriptions | jq '.by_topic'
```
Should include:
- `"raw.telemetry"` ← simulator publishes here
- `"risk.assessed"` ← risk processing publishes here
- `"case.state_changed"` ← cases update here
- `"ui.directive"` ← UI updates here

**If missing `raw.telemetry` subscriber**: The ws_bridge is not properly subscribed.
→ Check `backend/api/ws_session.py` line ~275 for `start_ws_bridge()` call
→ Check `backend/main.py` line ~63 to ensure `await start_ws_bridge(bus)` is called

#### Step 4: Trace a Test Event Through the Chain
```bash
# Terminal 1: Watch the backend logs while publishing
tail -f <your-log-file>

# Terminal 2: Publish a test event
curl -X POST "http://localhost:8000/api/debug/transport/test?topic=raw.telemetry" | jq

# Check results
curl http://localhost:8000/api/debug/transport/state | jq '.recent_events[-3:]'
curl http://localhost:8000/api/debug/transport/state | jq '.recent_broadcasts[-3:]'
```

Expected flow in logs:
```
🔵 EventBus.publish(raw.telemetry) — N/X subscribers | event=...
  ↓ (should match raw.telemetry subscriber)
📤 WS broadcast_all(raw.telemetry) → M total connections
  ↓ (should show broadcast to WS clients)
```

#### Step 5: Check WebSocket Connections
```bash
# Terminal 1: Start the frontend, open browser DevTools
# Network tab → WS: should see /ws/session/{id} connection

# Terminal 2: Check backend sees the connection
curl http://localhost:8000/api/debug/ws/connections | jq
```

Expected:
- `total_sessions: 1+`
- `total_connections: 1+`
- Session IDs match frontend console logs

#### Step 6: Monitor Frontend Socket Handler
In frontend browser console, add logging:

```typescript
// In frontend/src/ws/useSessionSocket.ts, add logging to onMessage:
socket.onMessage((msg) => {
  console.log('🔵 WS received:', msg.type, msg.payload)
  // ... rest of handler
})
```

Expected messages when simulator runs:
- `raw.telemetry` (sensor data)
- `risk.updated` (risk assessment)
- `case.state_changed` (case tier updates)

---

## How to Diagnose Chain 2 Breakage

### Symptom: Voice Input Not Reaching Backend Agent

#### Step 1: Check Voice Routes Are Registered
```bash
curl http://localhost:8000/api/debug/subscriptions | jq '.by_topic' | grep voice
```

Expected:
- `"voice.turn"` → voice interaction events
- `"voice.speak"` → TTS responses

#### Step 2: Test Voice Command Endpoint Directly
```bash
curl -X POST http://localhost:8000/api/voice/command \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "test-case",
    "text": "check the gas levels",
    "session_id": "test-session"
  }' | jq
```

Expected: 200 or 202 response with action data

#### Step 3: Check Agent Processing
Voice flow: `routes_voice_command.py` → `voice_agent.py` → `sensor_event_intelligence.py` → agents pipeline

Enable debug logging in `backend/agents/voice_agent.py`:

```python
logger.info("🎤 Processing voice input: %s", text)
logger.info("📊 Agent response: %s", response)
```

#### Step 4: Trace Through Event Bus
Voice commands may publish events like:
- `"voice.turn"` → voice interaction event
- `"normalized.events"` → if voice triggers sensor agent
- `"risk.assessed"` → if risk assessment needed

```bash
curl http://localhost:8000/api/debug/transport/state | jq '.by_topic' | grep voice
```

---

## Common Breakage Points

Based on code review, here are the likely issues:

### 🔴 **Critical: Event Bus Not Draining** 
**Symptom**: `queue_size` stays > 0

**Cause**: Event bus dispatch loop may be blocked or crashed

**Fix**:
```python
# In backend/bus/event_bus.py
# Check that _dispatch_loop is actually running
logger.info("EventBus: dispatch loop started")  # Should appear in logs

# Check no exception is killing the loop
# The loop should never crash — all handler exceptions are caught
```

### 🔴 **Critical: WS Bridge Not Subscribed**
**Symptom**: `raw.telemetry` has 0 subscribers

**Cause**: `start_ws_bridge(bus)` not called or failed silently

**Fix** (already applied in main.py):
```python
# backend/main.py lifespan
await bus.start()
await start_ws_bridge(bus)  # MUST call this
```

### 🟡 **Major: WebSocket Connections Not Accepted**
**Symptom**: Frontend connects but gets no messages

**Cause**: ConnectionManager not tracking the connection properly

**Debug**:
```bash
# In browser console when connecting:
console.log(sessionId)

# In backend:
curl http://localhost:8000/api/debug/ws/connections | jq
# Should show that session_id
```

### 🟡 **Major: Message Type Mismatch**
**Symptom**: Frontend receives messages but doesn't recognize type

**Cause**: Message type in broadcast doesn't match handler case

**Fix**:
Check `useSessionSocket.ts` message handler has cases for:
- `connection.status`
- `raw.telemetry` ← simulator events
- `risk.updated` ← risk assessments
- `case.state_changed` ← case updates
- etc.

---

## Testing Strategy

### Quick Smoke Test (60 seconds)

```bash
# 1. Start backend
python -m uvicorn backend.main:app --reload

# 2. In another terminal, run integration test
python -m backend.test_transport_chain

# Expected: 
# ✅ Chain 1 PASS
# ✅ Chain 2 PASS
```

### Detailed Diagnostic (5 minutes)

```bash
# Terminal 1: Watch backend logs
tail -f <logfile> | grep -E '(EventBus|WS|broadcast|🔵|📤)'

# Terminal 2: Monitor transport state
while true; do
  echo "=== $(date) ==="
  curl -s http://localhost:8000/api/debug/transport/state | jq '.event_bus,.websocket_connections'
  sleep 2
done

# Terminal 3: Run targeted test
curl -X POST http://localhost:8000/api/debug/transport/test | jq

# Terminal 4: Check subscriptions
curl http://localhost:8000/api/debug/subscriptions | jq
```

### Full Load Test (with simulator running)

```bash
# 1. Start backend with simulator enabled (default)
# 2. Connect frontend
# 3. Monitor:
curl http://localhost:8000/api/debug/transport/state | jq '.recent_broadcasts[-5:]'
curl http://localhost:8000/api/debug/ws/connections | jq

# Should see:
# - raw.telemetry broadcasts
# - risk.updated broadcasts  
# - increasing event counts
# - frontend clients receiving data
```

---

## Logs to Check

Enable detailed logging to find breakage:

```python
# backend/main.py
logging.basicConfig(
    level=logging.DEBUG,  # ← Set to DEBUG
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
```

Key log patterns to search for:

| Pattern | Meaning |
|---------|---------|
| `EventBus: dispatch loop started` | Bus is running ✅ |
| `WS bridge: subscribed to` | Bridge is active ✅ |
| `🔵 EventBus.publish` | Event being published |
| `📤 WS broadcast` | Event being broadcast to clients |
| `WS connect: session=` | Client connected |
| `handler raised` | Subscriber exception (detailed) |
| `no subscribers for topic` | Event published but no handlers (⚠️) |

---

## Quick Fixes Checklist

If Chain 1 is broken:

- [ ] Backend running? `curl http://localhost:8000/health`
- [ ] Event bus initialized? Check logs for "EventBus: dispatch loop started"
- [ ] WS bridge registered? Check for "WS bridge: subscribed to"
- [ ] Frontend WebSocket connected? Check `/api/debug/ws/connections`
- [ ] Message types match? Check `useSessionSocket.ts` cases
- [ ] Event listeners registered in store? Check Zustand hooks

If Chain 2 is broken:

- [ ] Voice route registered? Check `/api/debug/subscriptions`
- [ ] Voice handler function exists? Check `routes_voice_command.py`
- [ ] Agent initialized? Check agent imports and startup
- [ ] Event publishing to bus? Check agent code for `bus.publish()`
- [ ] Response reaching frontend? Check ws_bridge handlers for voice topics

---

## Next Steps

1. **Run the integration test**: `python -m backend.test_transport_chain`
2. **Check the debug endpoints**: Start with `/api/debug/transport/state`
3. **Follow the diagnostic steps** for whichever chain is failing
4. **Check the logs** for detailed error messages
5. **File issues** with the specific breakage point you identify

The debug tools will show you exactly where the data is stopping.
