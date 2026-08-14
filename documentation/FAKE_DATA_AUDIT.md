# NOVA Fake Data Audit

## Summary
- Total fake data sources found: 21
- Critical (blocks real demo): 10
- Medium (degrades accuracy): 10
- Low (cosmetic/labels): 1

## Findings

### FINDING-001
- File: `backend/agents/voice_agent.py`
- Lines: 288-304
- Category: hardcoded string responses
- Severity: critical
- Description: voice_agent.py returns canned hardcoded responses ('Bay 3 C-14 compressor...', 'Bay 4 flare header...', 'All five operational bays...') when LLM calls fail or rate limit.
- Real data source that should replace it: Groq LLM completion response or 10-second timeout fallback object.
- Fix: Remove all canned strings. On LLM failure or timeout, return standardized timeout/error dict as required by Rule G. Add # REAL: comment.

### FINDING-002
- File: `backend/services/groq_client.py`
- Lines: 13, 36, 45, 70
- Category: fallback data in catch blocks and error handlers
- Severity: critical
- Description: groq_client.py returns hardcoded fallback string 'status nominal, awaiting details' or empty dict when GROQ_API_KEY is missing or API errors.
- Real data source that should replace it: Real Groq API completion response.
- Fix: Raise RuntimeError / exception on missing key or API failure so caller handles real error state. Add # REAL: comment.

### FINDING-003
- File: `backend/api/routes_risk.py`
- Lines: 24-41
- Category: backend routes returning hardcoded dicts
- Severity: critical
- Description: GET /api/zones returns hardcoded stub dicts for 'zone-a' and 'zone-b' with fake compound scores.
- Real data source that should replace it: SQLite cases database table and active factory risk state.
- Fix: Replace hardcoded stub return with DB query from cases table and factory state zones. Add # REAL: comment.

### FINDING-004
- File: `src/engine/realSystemEngine.ts`
- Lines: 172-211
- Category: voice/LLM response shortcuts
- Severity: critical
- Description: fallbackReAct function returns hardcoded voice response strings when Groq API call fails.
- Real data source that should replace it: Backend POST /api/voice/query or live store state.
- Fix: Remove fallbackReAct canned responses. Log error and return error status. Add // REAL: comment.

### FINDING-005
- File: `frontend/src/engine/realSystemEngine.ts`
- Lines: 172-211
- Category: voice/LLM response shortcuts
- Severity: critical
- Description: frontend/src/engine/realSystemEngine.ts fallbackReAct returns hardcoded voice response strings on Groq failure.
- Real data source that should replace it: Backend POST /api/voice/query or live store state.
- Fix: Remove fallbackReAct canned strings and handle real API error. Add // REAL: comment.

### FINDING-006
- File: `src/engine/novaSpeech.ts`
- Lines: 210-225
- Category: hardcoded string responses
- Severity: critical
- Description: novaSpeech.ts contains fallback canned voice responses for unhandled operator speech.
- Real data source that should replace it: Groq LLM pipeline response from POST /api/voice/query.
- Fix: Wire speech handler directly to backend voice query pipeline. Add // REAL: comment.

### FINDING-007
- File: `frontend/src/pages/FridayCoPilot.tsx`
- Lines: 30-45
- Category: voice/LLM response shortcuts
- Severity: critical
- Description: FridayCoPilot.tsx uses hardcoded NOVA_RESPONSES dictionary mapping operator questions to static text responses.
- Real data source that should replace it: Backend POST /api/voice/query API endpoint.
- Fix: Remove NOVA_RESPONSES map and query POST /api/voice/query endpoint dynamically. Add // REAL: comment.

### FINDING-008
- File: `frontend/src/pages/RetrievalTrace.tsx`
- Lines: 27-35
- Category: inline mock objects and arrays
- Severity: critical
- Description: RetrievalTrace.tsx renders hardcoded mock retrieval matches ('INC-2024-1182', 'Bay 3 H₂S + PTW overlap').
- Real data source that should replace it: GET /api/memory/retrieval-trace/:caseId API endpoint.
- Fix: Fetch real retrieval traces via getRetrievalTrace(caseId) API call. Add // REAL: comment.

### FINDING-009
- File: `frontend/src/pages/SensorTelemetry.tsx`
- Lines: 19-40
- Category: inline mock objects and arrays
- Severity: critical
- Description: SensorTelemetry.tsx initializes telemetry UI with DEMO_SENSORS static mock array.
- Real data source that should replace it: WebSocket sensorStream via useCaseStore.
- Fix: Remove DEMO_SENSORS and subscribe directly to WebSocket sensorStream. Add // REAL: comment.

### FINDING-010
- File: `backend/api/routes_voice_command.py`
- Lines: 71, 102
- Category: hardcoded string responses
- Severity: critical
- Description: routes_voice_command.py returns hardcoded briefing string ('While you were away, 142 telemetry parameters...') on Groq LLM error.
- Real data source that should replace it: Backend LLM briefing generator pipeline.
- Fix: Raise HTTPException 500 on LLM briefing generation failure instead of returning canned text. Add # REAL: comment.

### FINDING-011
- File: `src/engine/realSystemEngine.ts`
- Lines: 36-55
- Category: random/fake data generation
- Severity: medium
- Description: startLiveTelemetryStream generates client-side sensor values using Math.sin() and Math.random().
- Real data source that should replace it: WebSocket sensorStream from backend event bus / data simulator.
- Fix: Remove client-side Math.random drift generator and subscribe component to real WS sensorStream store. Add // REAL: comment.

### FINDING-012
- File: `frontend/src/engine/realSystemEngine.ts`
- Lines: 36-55
- Category: random/fake data generation
- Severity: medium
- Description: frontend/src/engine/realSystemEngine.ts generates client-side sensor values using Math.sin() and Math.random().
- Real data source that should replace it: WebSocket sensorStream from backend event bus / data simulator.
- Fix: Remove client-side Math.random telemetry loop and rely on real WS feed. Add // REAL: comment.

### FINDING-013
- File: `src/engine/demoOrchestrator.ts`
- Lines: 18, 24, 28, 37, 41
- Category: random/fake data generation
- Severity: medium
- Description: demoOrchestrator.ts uses Math.random() to generate random jitter on sensor values.
- Real data source that should replace it: Real backend scenario runner or WS event payload.
- Fix: Remove Math.random jitter generation. Add // REAL: comment.

### FINDING-014
- File: `src/pages/LiveInteraction.tsx`
- Lines: 40
- Category: random/fake data generation
- Severity: medium
- Description: LiveInteraction.tsx uses Math.random() to simulate microphone visualizer bar heights.
- Real data source that should replace it: Real Web Audio API AnalyserNode frequency data.
- Fix: Use real AudioContext AnalyserNode frequency data. Add // REAL: comment.

### FINDING-015
- File: `frontend/src/store/useDemoStore.ts`
- Lines: 124
- Category: random/fake data generation
- Severity: medium
- Description: useDemoStore.ts uses Math.random() to generate event IDs.
- Real data source that should replace it: crypto.randomUUID() web standard API.
- Fix: Replace Math.random() with crypto.randomUUID(). Add // REAL: comment.

### FINDING-016
- File: `frontend/src/store/useSimulationStore.ts`
- Lines: 169
- Category: random/fake data generation
- Severity: medium
- Description: useSimulationStore.ts uses Math.random() to generate event IDs.
- Real data source that should replace it: crypto.randomUUID() web standard API.
- Fix: Replace Math.random() with crypto.randomUUID(). Add // REAL: comment.

### FINDING-017
- File: `src/store/useDemoStore.ts`
- Lines: 138
- Category: random/fake data generation
- Severity: medium
- Description: src/store/useDemoStore.ts uses Math.random() for event IDs.
- Real data source that should replace it: crypto.randomUUID() web standard API.
- Fix: Replace Math.random() with crypto.randomUUID(). Add // REAL: comment.

### FINDING-018
- File: `src/store/useSimulationStore.ts`
- Lines: 130
- Category: random/fake data generation
- Severity: medium
- Description: src/store/useSimulationStore.ts uses Math.random() for event IDs.
- Real data source that should replace it: crypto.randomUUID() web standard API.
- Fix: Replace Math.random() with crypto.randomUUID(). Add // REAL: comment.

### FINDING-019
- File: `backend/api/routes_memory.py`
- Lines: 293
- Category: fallback data in catch blocks and error handlers
- Severity: medium
- Description: store_critical_incident catch block returns fake stub record_id 'stub-{req.zone_id}-{req.sensor_type}' on Qdrant error.
- Real data source that should replace it: Qdrant write response or HTTP 500 error exception.
- Fix: Raise HTTPException(status_code=500, detail=str(e)) instead of returning fake stub id. Add # REAL: comment.

### FINDING-020
- File: `backend/tools/permit_suspend.py`
- Lines: 57, 89, 92
- Category: fallback data in catch blocks and error handlers
- Severity: medium
- Description: permit_suspend.py catch block returns fake permit status dicts on database/permit error.
- Real data source that should replace it: Real SQLite permit status or exception.
- Fix: Raise Exception on permit error instead of returning fake success/status dict. Add # REAL: comment.

### FINDING-021
- File: `src/pages/Auth.tsx`
- Lines: 66, 77
- Category: useEffect / setInterval with fake data injections
- Severity: low
- Description: Auth.tsx uses setTimeout timer to inject mock authorization status.
- Real data source that should replace it: POST /api/cases/:caseId/authorize endpoint.
- Fix: Replace setTimeout with real API call to authorize endpoint. Add // REAL: comment.

