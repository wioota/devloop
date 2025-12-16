"""Tests for agent signing and verification."""

import json
import pytest
import tempfile
from pathlib import Path

from devloop.marketplace.signing import (
    AgentSignature,
    AgentSigner,
    AgentVerifier,
)


@pytest.fixture
def temp_agent_dir():
    """Create a temporary agent directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        agent_dir = Path(tmpdir)

        # Create agent.json
        agent_json = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test agent",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
        }

        with open(agent_dir / "agent.json", "w") as f:
            json.dump(agent_json, f)

        # Create some implementation files
        (agent_dir / "__init__.py").write_text("# Implementation")
        (agent_dir / "main.py").write_text("# Main handler")

        yield agent_dir


class TestAgentSignature:
    """Test AgentSignature class."""

    def test_signature_initialization(self):
        """Test creating a signature."""
        sig = AgentSignature(
            signer="test-author",
            timestamp="2024-12-13T00:00:00",
            checksum="abc123",
        )

        assert sig.signer == "test-author"
        assert sig.checksum == "abc123"

    def test_signature_to_dict(self):
        """Test converting signature to dict."""
        sig = AgentSignature(
            signer="test-author",
            timestamp="2024-12-13T00:00:00",
            checksum="abc123",
            metadata_hash="def456",
        )

        sig_dict = sig.to_dict()

        assert sig_dict["signer"] == "test-author"
        assert sig_dict["checksum"] == "abc123"
        assert sig_dict["metadata_hash"] == "def456"

    def test_signature_from_dict(self):
        """Test creating signature from dict."""
        data = {
            "signer": "test-author",
            "timestamp": "2024-12-13T00:00:00",
            "checksum": "abc123",
            "signature_method": "sha256",
            "metadata_hash": "def456",
        }

        sig = AgentSignature.from_dict(data)

        assert sig.signer == "test-author"
        assert sig.checksum == "abc123"


class TestAgentSigner:
    """Test AgentSigner class."""

    def test_signer_initialization(self):
        """Test creating a signer."""
        signer = AgentSigner("test-author")
        assert signer.signer_id == "test-author"

    def test_sign_agent(self, temp_agent_dir):
        """Test signing an agent."""
        signer = AgentSigner("test-author")
        success, signature = signer.sign_agent(temp_agent_dir)

        assert success is True
        assert signature is not None
        assert signature.signer == "test-author"
        assert len(signature.checksum) == 64  # SHA256

    def test_sign_agent_missing_metadata(self, temp_agent_dir):
        """Test signing with missing metadata."""
        (temp_agent_dir / "agent.json").unlink()

        signer = AgentSigner("test-author")
        success, signature = signer.sign_agent(temp_agent_dir)

        assert success is False
        assert signature is None

    def test_sign_agent_multiple_calls(self, temp_agent_dir):
        """Test signing produces consistent checksums."""
        signer = AgentSigner("test-author")

        success1, sig1 = signer.sign_agent(temp_agent_dir)
        success2, sig2 = signer.sign_agent(temp_agent_dir)

        assert success1 and success2
        assert sig1.checksum == sig2.checksum

    def test_signature_changes_with_metadata(self, temp_agent_dir):
        """Test that signature changes when metadata changes."""
        signer = AgentSigner("test-author")

        # Sign original
        success1, sig1 = signer.sign_agent(temp_agent_dir)
        assert success1

        # Modify metadata
        with open(temp_agent_dir / "agent.json") as f:
            data = json.load(f)
        data["version"] = "2.0.0"
        with open(temp_agent_dir / "agent.json", "w") as f:
            json.dump(data, f)

        # Sign again
        success2, sig2 = signer.sign_agent(temp_agent_dir)
        assert success2

        # Signatures should differ
        assert sig1.checksum != sig2.checksum

    def test_save_signature(self, temp_agent_dir):
        """Test saving signature to file."""
        signer = AgentSigner("test-author")
        success, signature = signer.sign_agent(temp_agent_dir)

        assert success

        # Save signature
        saved = signer.save_signature(temp_agent_dir, signature)

        assert saved is True

        # Verify file exists
        sig_file = temp_agent_dir / ".agent-signature.json"
        assert sig_file.exists()

        # Verify content
        with open(sig_file) as f:
            data = json.load(f)
        assert data["signer"] == "test-author"


class TestAgentVerifier:
    """Test AgentVerifier class."""

    def test_verify_signed_agent(self, temp_agent_dir):
        """Test verifying a properly signed agent."""
        # Sign first
        signer = AgentSigner("test-author")
        success, signature = signer.sign_agent(temp_agent_dir)
        signer.save_signature(temp_agent_dir, signature)

        # Then verify
        is_valid, details = AgentVerifier.verify_agent(temp_agent_dir)

        assert is_valid is True
        assert details["valid"] is True
        assert details["checks"]["metadata_exists"] is True
        assert details["checks"]["checksum_valid"] is True

    def test_verify_unsigned_agent(self, temp_agent_dir):
        """Test verifying agent without signature."""
        is_valid, details = AgentVerifier.verify_agent(temp_agent_dir)

        assert is_valid is False
        assert "No signature found" in details.get("error", "")

    def test_verify_tampered_agent(self, temp_agent_dir):
        """Test verifying agent with tampered metadata."""
        # Sign first
        signer = AgentSigner("test-author")
        success, signature = signer.sign_agent(temp_agent_dir)
        signer.save_signature(temp_agent_dir, signature)

        # Tamper with metadata
        with open(temp_agent_dir / "agent.json") as f:
            data = json.load(f)
        data["version"] = "2.0.0"
        with open(temp_agent_dir / "agent.json", "w") as f:
            json.dump(data, f)

        # Verify should fail
        is_valid, details = AgentVerifier.verify_agent(temp_agent_dir)

        assert is_valid is False
        assert details["checks"]["checksum_valid"] is False

    def test_verify_with_directory_hash(self, temp_agent_dir):
        """Test verification with directory hash."""
        # Sign with directory hash
        signer = AgentSigner("test-author")
        success, signature = signer.sign_agent(temp_agent_dir)

        # Verify metadata hash is present
        assert signature.metadata_hash is not None

        signer.save_signature(temp_agent_dir, signature)

        # Verify - metadata should be valid, but directory hash will differ
        # because we added the signature file
        is_valid, details = AgentVerifier.verify_agent(temp_agent_dir)

        # Metadata checksum should be valid
        assert details["checks"]["checksum_valid"] is True

        # Directory hash will differ due to signature file being added
        # This is expected behavior
        if "directory_hash_valid" in details["checks"]:
            # We expect it to be False since we added the signature file
            # after calculating the hash
            assert details["checks"]["directory_hash_valid"] is False

    def test_verify_with_modified_files(self, temp_agent_dir):
        """Test verification detects modified files."""
        # Sign first
        signer = AgentSigner("test-author")
        success, signature = signer.sign_agent(temp_agent_dir)
        signer.save_signature(temp_agent_dir, signature)

        # Modify a non-metadata file
        (temp_agent_dir / "main.py").write_text("# Modified")

        # Verify
        is_valid, details = AgentVerifier.verify_agent(temp_agent_dir)

        # Metadata should still be valid
        assert details["checks"]["checksum_valid"] is True

        # But directory hash should show warning
        if signature.metadata_hash:
            assert details["checks"]["directory_hash_valid"] is False

    def test_get_signature_info(self, temp_agent_dir):
        """Test getting signature info."""
        # Sign first
        signer = AgentSigner("test-author")
        success, signature = signer.sign_agent(temp_agent_dir)
        signer.save_signature(temp_agent_dir, signature)

        # Get info
        info = AgentVerifier.get_signature_info(temp_agent_dir)

        assert info is not None
        assert info["signer"] == "test-author"

    def test_get_signature_info_unsigned(self, temp_agent_dir):
        """Test getting signature info for unsigned agent."""
        info = AgentVerifier.get_signature_info(temp_agent_dir)

        assert info is None


class TestSigningWorkflow:
    """Test complete signing/verification workflows."""

    def test_sign_and_verify_workflow(self, temp_agent_dir):
        """Test complete sign and verify workflow."""
        signer = AgentSigner("john-doe")

        # 1. Sign agent
        success, signature = signer.sign_agent(temp_agent_dir)
        assert success

        # 2. Save signature
        saved = signer.save_signature(temp_agent_dir, signature)
        assert saved

        # 3. Verify signature
        is_valid, details = AgentVerifier.verify_agent(temp_agent_dir)
        assert is_valid

        # 4. Get signature info
        info = AgentVerifier.get_signature_info(temp_agent_dir)
        assert info["signer"] == "john-doe"

    def test_update_and_resign_workflow(self, temp_agent_dir):
        """Test updating and re-signing an agent."""
        signer = AgentSigner("john-doe")

        # 1. Sign original
        success1, sig1 = signer.sign_agent(temp_agent_dir)
        signer.save_signature(temp_agent_dir, sig1)

        # Verify works
        is_valid1, _ = AgentVerifier.verify_agent(temp_agent_dir)
        assert is_valid1

        # 2. Update agent
        with open(temp_agent_dir / "agent.json") as f:
            data = json.load(f)
        data["version"] = "2.0.0"
        with open(temp_agent_dir / "agent.json", "w") as f:
            json.dump(data, f)

        # Verification should fail now (metadata changed)
        is_valid2, details = AgentVerifier.verify_agent(temp_agent_dir)
        assert is_valid2 is False

        # 3. Re-sign
        success2, sig2 = signer.sign_agent(temp_agent_dir)
        signer.save_signature(temp_agent_dir, sig2)

        # Verification should work again
        is_valid3, _ = AgentVerifier.verify_agent(temp_agent_dir)
        assert is_valid3


if __name__ == "__main__":
    pytest.main([__file__])
