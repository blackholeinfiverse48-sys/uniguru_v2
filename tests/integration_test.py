import unittest
import json
import hashlib
from typing import Dict, Any
from uniguru.enforcement.seal import EnforcementSealer
from uniguru.enforcement.enforcement import SovereignEnforcement
from uniguru.retrieval.retriever import AdvancedRetriever

class TestUniGuruBridgeIntegration(unittest.TestCase):
    """
    End-to-End Integration Test for UniGuru Bridge v2.1.
    Validates: Sealing, Multi-Source Retrieval, Global Verification.
    """

    def setUp(self):
        self.sealer = EnforcementSealer()
        self.enforcer = SovereignEnforcement()
        self.retriever = AdvancedRetriever()

    def test_cryptographic_seal(self):
        """GAP 1: Test that every response is sealed and verified."""
        content = "The core of Jainism is non-violence (Ahimsa)."
        request_id = "test-req-123"
        
        # Simulate decision
        decision = {
            "decision": "answer",
            "verification_status": "VERIFIED",
            "data": {"response_content": content}
        }
        
        # Enforce and Seal
        sealed = self.enforcer.process_and_seal(decision, request_id)
        
        self.assertIn("enforcement_signature", sealed)
        self.assertTrue(sealed["enforced"])
        
        # Verify Seal
        is_valid = self.enforcer.verify_bridge_seal(sealed)
        self.assertTrue(is_valid, "Signature should be valid for authentic content.")
        
        # Test Tampering
        sealed["data"]["response_content"] = "TAMPERED CONTENT"
        is_invalid = self.enforcer.verify_bridge_seal(sealed)
        self.assertFalse(is_invalid, "Bridge must detect tampering.")

    def test_multi_source_retrieval(self):
        """GAP 2: Test multi-document reasoning logic."""
        # Broaden query to ensure multiple matches across expanded KB
        query = "sutra vachanamrut"
        results = self.retriever.retrieve_multi(query)
        
        self.assertGreaterEqual(len(results), 1, "Retriever should find at least one document.")
        
        comparison = self.retriever.reason_and_compare(results)
        self.assertIn("reasoning", comparison)
        self.assertIn("RETRIEVED", comparison["reasoning"].upper())

    def test_global_verification_refusal(self):
        """GAP 3: Test that UNVERIFIED content is refused."""
        request_id = "test-req-refuse"
        
        # Simulate an unverified decision
        unverified_decision = {
            "decision": "answer",
            "verification_status": "UNVERIFIED",
            "data": {"response_content": "Random unverified claim."}
        }
        
        sealed = self.enforcer.process_and_seal(unverified_decision, request_id)
        
        self.assertEqual(sealed["decision"], "block", "UNVERIFIED must trigger block.")
        self.assertEqual(sealed["status_action"], "REFUSE")
        self.assertEqual(
            sealed["data"]["response_content"],
            "Verification status: UNVERIFIED. I cannot verify this information from current knowledge."
        )

    def test_forwarding_structure(self):
        """GAP 4: Test that forwarded responses are processed for sealing."""
        request_id = "test-req-forward"
        
        # Simulate a response from Production UniGuru
        legacy_data = {"answer": "Production result content.", "trace": "prod-trace-1"}
        
        forward_decision = {
            "decision": "forward",
            "legacy_response": legacy_data,
            "verification_status": "PARTIAL"
        }
        
        sealed = self.enforcer.process_and_seal(forward_decision, request_id)
        
        self.assertIn("enforce", str(sealed.keys()).lower())
        self.assertIn("enforcement_signature", sealed)
        self.assertEqual(sealed["status_action"], "ALLOW_WITH_DISCLAIMER")

if __name__ == "__main__":
    unittest.main()
