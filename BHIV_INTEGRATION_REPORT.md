# BHIV_INTEGRATION_REPORT

## Scope
UniGuru integration validation against BHIV ecosystem callers and contract requirements.

## Integrated Callers
- `bhiv-assistant`
- `gurukul-platform`
- `internal-testing`

## Interface Contract
- Endpoint: `POST /ask`
- Auth: `Authorization: Bearer <UNIGURU_API_TOKEN>`
- Caller identity: `context.caller` or `X-Caller-Name`
- Required response fields verified: `ontology_reference`, `verification_status`, `reasoning_trace`

## Validation Evidence
- Automated API tests: `pytest -q tests/test_registry_api.py`
- Result: `12 passed`
- Evidence file: `demo_logs/integration_test_evidence.json`
- Service stability evidence: `demo_logs/service_stability_evidence.json`

## Scenario Results
1. Verified knowledge query: PASS (`decision=answer`, `verification_status=VERIFIED`)
2. Unknown query: PASS (`decision=block`, deterministic refusal)
3. Unsafe query: PASS (governance/enforcement block)
4. Web retrieval query: PASS (reasoning trace and verification metadata present)

## Integration Outcome
UniGuru is compatible with BHIV assistant routing and Gurukul adapter usage through authenticated, caller-governed API invocation.
