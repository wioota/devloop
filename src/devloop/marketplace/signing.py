"""Agent package signing and verification."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentSignature:
    """Signature metadata for an agent."""

    def __init__(
        self,
        signer: str,
        timestamp: str,
        checksum: str,
        signature_method: str = "sha256",
        metadata_hash: Optional[str] = None,
    ):
        """Initialize signature.

        Args:
            signer: Name/ID of the signer
            timestamp: ISO 8601 timestamp when signed
            checksum: Checksum of signed content
            signature_method: Method used (sha256, etc)
            metadata_hash: Hash of agent metadata
        """
        self.signer = signer
        self.timestamp = timestamp
        self.checksum = checksum
        self.signature_method = signature_method
        self.metadata_hash = metadata_hash

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "signer": self.signer,
            "timestamp": self.timestamp,
            "checksum": self.checksum,
            "signature_method": self.signature_method,
            "metadata_hash": self.metadata_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentSignature":
        """Create from dictionary."""
        return cls(
            signer=data["signer"],
            timestamp=data["timestamp"],
            checksum=data["checksum"],
            signature_method=data.get("signature_method", "sha256"),
            metadata_hash=data.get("metadata_hash"),
        )


class AgentSigner:
    """Sign agent packages for verification."""

    def __init__(self, signer_id: str):
        """Initialize signer.

        Args:
            signer_id: Identifier for the signer (e.g., author name, organization)
        """
        self.signer_id = signer_id

    def sign_agent(
        self,
        agent_dir: Path,
        metadata_file: str = "agent.json",
    ) -> Tuple[bool, Optional[AgentSignature]]:
        """Sign an agent package.

        Args:
            agent_dir: Directory containing agent
            metadata_file: Name of metadata file to sign

        Returns:
            Tuple of (success, signature)
        """
        try:
            metadata_path = agent_dir / metadata_file

            if not metadata_path.exists():
                logger.error(f"Metadata file not found: {metadata_path}")
                return False, None

            # Calculate checksum of metadata
            with open(metadata_path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()

            # Also calculate hash of entire agent directory
            directory_hash = self._hash_directory(agent_dir)

            signature = AgentSignature(
                signer=self.signer_id,
                timestamp=datetime.now().isoformat(),
                checksum=checksum,
                signature_method="sha256",
                metadata_hash=directory_hash,
            )

            logger.info(f"Signed agent in {agent_dir}")
            return True, signature

        except Exception as e:
            logger.error(f"Failed to sign agent: {e}")
            return False, None

    def _hash_directory(self, directory: Path) -> str:
        """Calculate hash of directory contents.

        Args:
            directory: Directory to hash

        Returns:
            SHA256 hash of directory
        """
        hasher = hashlib.sha256()

        # Sort files for consistent hashing
        for filepath in sorted(directory.rglob("*")):
            if filepath.is_file():
                with open(filepath, "rb") as f:
                    hasher.update(f.read())

        return hasher.hexdigest()

    def save_signature(
        self,
        agent_dir: Path,
        signature: AgentSignature,
        signature_file: str = ".agent-signature.json",
    ) -> bool:
        """Save signature to file.

        Args:
            agent_dir: Directory containing agent
            signature: Signature to save
            signature_file: Name of signature file

        Returns:
            Success indicator
        """
        try:
            signature_path = agent_dir / signature_file

            with open(signature_path, "w") as f:
                json.dump(signature.to_dict(), f, indent=2)

            logger.info(f"Saved signature to {signature_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save signature: {e}")
            return False


class AgentVerifier:
    """Verify signed agent packages."""

    @staticmethod
    def verify_agent(
        agent_dir: Path,
        signature_file: str = ".agent-signature.json",
        metadata_file: str = "agent.json",
    ) -> Tuple[bool, Dict]:
        """Verify agent signature.

        Args:
            agent_dir: Directory containing agent
            signature_file: Name of signature file
            metadata_file: Name of metadata file

        Returns:
            Tuple of (is_valid, verification_details)
        """
        details: Dict[str, Any] = {
            "valid": False,
            "agent_dir": str(agent_dir),
            "checks": {},
        }

        try:
            # Load signature
            sig_path = agent_dir / signature_file
            if not sig_path.exists():
                details["error"] = f"No signature found: {sig_path}"
                return False, details

            with open(sig_path) as f:
                sig_data = json.load(f)

            signature = AgentSignature.from_dict(sig_data)
            details["signature"] = signature.to_dict()

            # Check metadata file exists
            metadata_path = agent_dir / metadata_file
            if not metadata_path.exists():
                details["checks"]["metadata_exists"] = False
                return False, details

            details["checks"]["metadata_exists"] = True

            # Verify metadata checksum
            with open(metadata_path, "rb") as f:
                current_checksum = hashlib.sha256(f.read()).hexdigest()

            checksum_valid = current_checksum == signature.checksum
            details["checks"]["checksum_valid"] = checksum_valid
            details["current_checksum"] = current_checksum

            if not checksum_valid:
                details["error"] = "Metadata checksum mismatch"
                return False, details

            # Verify directory hash if available
            if signature.metadata_hash:
                directory_hash = AgentSigner("")._hash_directory(agent_dir)
                hash_valid = directory_hash == signature.metadata_hash
                details["checks"]["directory_hash_valid"] = hash_valid
                details["current_directory_hash"] = directory_hash

                if not hash_valid:
                    details["warning"] = "Directory contents have changed"

            details["checks"]["signature_valid"] = True
            details["valid"] = True
            return True, details

        except Exception as e:
            logger.error(f"Failed to verify agent: {e}")
            details["error"] = str(e)
            return False, details

    @staticmethod
    def get_signature_info(
        agent_dir: Path, signature_file: str = ".agent-signature.json"
    ) -> Optional[Dict]:
        """Get information about an agent's signature.

        Args:
            agent_dir: Directory containing agent
            signature_file: Name of signature file

        Returns:
            Signature info or None
        """
        try:
            sig_path = agent_dir / signature_file

            if not sig_path.exists():
                return None

            with open(sig_path) as f:
                result: Dict[Any, Any] = json.load(f)
                return result

        except Exception as e:
            logger.error(f"Failed to get signature info: {e}")
            return None
