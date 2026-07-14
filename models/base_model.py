from abc import ABC, abstractmethod
from typing import Any


class BaseModel(ABC):

    name = "Base Model"

    @abstractmethod
    def predict(self, state) -> dict[str, Any]:
        """
        Returns

        {
            prediction,
            confidence,
            probability,
            reasons
        }
        """
        raise NotImplementedError