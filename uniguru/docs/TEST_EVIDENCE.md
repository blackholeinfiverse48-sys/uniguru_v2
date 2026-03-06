# UniGuru Live Service Test Evidence

## Automated Test Suite
- Command: `python -m pytest uniguru/tests/test_live_service.py -q`
- Result: `4 passed`

## Scenario Logs
Structured logs generated at:
- `demo_logs/uniguru_live_service_test_evidence.json`

Included scenarios:
1. `verified_kb_response`
2. `unverified_web_response`
3. `unknown_question`
4. `blocked_unsafe_query`

