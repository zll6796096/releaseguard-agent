from abc import ABC, abstractmethod
from typing import List
from app.models import EvaluationRequest, EvidenceItem

class BaseSkill(ABC):
    """Abstract base class for all ReleaseGuard skills/probes."""

    @abstractmethod
    async def evaluate(self, request: EvaluationRequest) -> List[EvidenceItem]:
        """Runs the evaluation probe against the request data.

        Args:
            request (EvaluationRequest): The incoming release request validation parameters.

        Returns:
            List[EvidenceItem]: The list of gathered evidence items.
        """
        pass
