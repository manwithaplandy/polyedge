"""Base class for data sources."""

from abc import ABC, abstractmethod
from typing import Any


class DataSourceBase(ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the data source is available."""
        pass

    @abstractmethod
    async def fetch(self, **kwargs: Any) -> Any:
        """Fetch data from the source."""
        pass
