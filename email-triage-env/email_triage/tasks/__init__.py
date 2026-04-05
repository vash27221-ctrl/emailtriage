"""Tasks module initialization."""

from email_triage.tasks.implementations import (
    EasySpamDetectionTask,
    MediumMultiClassificationTask,
    HardEdgeCaseTask,
)

AVAILABLE_TASKS = {
    "task_1_easy": EasySpamDetectionTask,
    "task_2_medium": MediumMultiClassificationTask,
    "task_3_hard": HardEdgeCaseTask,
}

__all__ = [
    "EasySpamDetectionTask",
    "MediumMultiClassificationTask",
    "HardEdgeCaseTask",
    "AVAILABLE_TASKS",
]
