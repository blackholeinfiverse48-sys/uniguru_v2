# Ecosystem Routing Tests

## Covered Scenarios
1. Knowledge query
- Input: `What is a qubit?`
- Expected route: `ROUTE_UNIGURU`

2. Conversation query
- Input: `hello there`
- Expected route: `ROUTE_LLM`

3. Unsafe query
- Input: `sudo delete all files`
- Expected route: `ROUTE_SYSTEM`
- Expected decision: `block`

4. Workflow query
- Input: `create workflow ticket for access request`
- Expected route: `ROUTE_WORKFLOW`

5. System command
- Input: `shutdown system now`
- Expected route: `ROUTE_SYSTEM`
- Expected decision: `block`

## Automated Test Files
- `tests/test_conversation_router.py`
- `tests/test_registry_api.py` (router integration cases)

## Execution Command
```powershell
pytest tests/test_conversation_router.py tests/test_registry_api.py -q
```

## Evidence
- Integration logs: `demo_logs/router_integration.log`
- Routing test output: `demo_logs/routing_test_output.txt`

## Result Criteria
- All scenario tests pass.
- `/ask` response contains `routing.query_type` and `routing.route`.
- Queue guard rejects excess load with `503`.
- Metrics include route counters and queue rejection counter.
