from dataclasses import dataclass
from datetime import datetime


@dataclass
class PipelineResult:

    step: str

    success: bool

    started_at: datetime

    finished_at: datetime

    records_processed: int = 0

    message: str = ""

    error: str | None = None

    @property
    def duration(self):

        return self.finished_at - self.started_at