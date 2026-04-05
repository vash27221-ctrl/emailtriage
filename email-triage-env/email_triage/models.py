"""Typed Pydantic models for OpenEnv compliance."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EmailCategory(str, Enum):
    """Email classification categories."""
    SPAM = "spam"
    URGENT = "urgent"
    FOLLOW_UP = "follow_up"
    INFORMATIONAL = "informational"
    ARCHIVED = "archived"


class ActionType(str, Enum):
    """Possible agent actions."""
    CLASSIFY = "classify"
    READ_MORE = "read_more"
    FLAG = "flag"
    ARCHIVE = "archive"
    SKIP = "skip"


class Action(BaseModel):
    """Agent action model."""
    action_type: ActionType = Field(
        description="Type of action to perform"
    )
    category: Optional[EmailCategory] = Field(
        default=None,
        description="Target category for classification"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Brief reason for the action"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "action_type": "classify",
                "category": "urgent",
                "reason": "Contains security alert"
            }
        }


class Email(BaseModel):
    """Email data model."""
    id: str = Field(description="Unique email identifier")
    sender: str = Field(description="Email sender address")
    subject: str = Field(description="Email subject line")
    preview: str = Field(description="Email body preview (truncated)")
    received_time: str = Field(description="ISO format timestamp")
    is_reply: bool = Field(description="Whether this is a reply")
    has_attachment: bool = Field(description="Whether email has attachments")
    ground_truth_category: EmailCategory = Field(
        description="Correct classification (hidden from agent during episode)"
    )


class Observation(BaseModel):
    """Environment observation model."""
    current_email: Email = Field(description="Current email being processed")
    processed_count: int = Field(description="Number of emails processed so far")
    total_count: int = Field(description="Total emails in this batch")
    correct_classifications: int = Field(
        description="Count of correct classifications made"
    )
    task_id: str = Field(description="Current task identifier")
    hint: Optional[str] = Field(
        default=None,
        description="Optional hint for current email (task-dependent)"
    )
    
    def model_post_init(self, __context):
        """Hide ground truth from observation if present."""
        # Ensure ground truth is not exposed in observation
        if hasattr(self.current_email, 'ground_truth_category'):
            # Keep for internal validation but don't serialize it in normal views
            pass

    class Config:
        json_schema_extra = {
            "example": {
                "current_email": {
                    "id": "email_1",
                    "sender": "security@example.com",
                    "subject": "URGENT: Security Alert - Login from new device",
                    "preview": "Your account security has triggered an alert...",
                    "received_time": "2026-04-04T10:30:00Z",
                    "is_reply": False,
                    "has_attachment": False,
                    "ground_truth_category": "urgent"
                },
                "processed_count": 1,
                "total_count": 10,
                "correct_classifications": 0,
                "task_id": "task_1_easy",
                "hint": "Check if the subject contains urgent indicators"
            }
        }


class Reward(BaseModel):
    """Reward signal model."""
    step_reward: float = Field(
        ge=0.0,
        le=1.0,
        description="Reward for this step (0.0-1.0)"
    )
    cumulative_reward: float = Field(
        ge=0.0,
        le=1.0,
        description="Cumulative episode reward (0.0-1.0)"
    )
    accuracy: float = Field(
        ge=0.0,
        le=1.0,
        description="Current accuracy on correctly classified emails"
    )
    bonus: float = Field(
        default=0.0,
        description="Bonus for exceptional performance"
    )
    penalty: float = Field(
        default=0.0,
        description="Penalty for errors"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "step_reward": 0.25,
                "cumulative_reward": 0.25,
                "accuracy": 1.0,
                "bonus": 0.0,
                "penalty": 0.0
            }
        }


class StateSnapshot(BaseModel):
    """Complete state snapshot at any point."""
    task_id: str = Field(description="Task identifier")
    episode_step: int = Field(description="Current step in episode")
    current_email_id: str = Field(description="Current email ID")
    emails_processed: List[Dict[str, Any]] = Field(
        description="History of processed emails and actions"
    )
    total_correct: int = Field(description="Total correct classifications")
    total_wrong: int = Field(description="Total wrong classifications")
    cumulative_reward: float = Field(
        ge=0.0,
        le=1.0,
        description="Cumulative reward so far"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_1_easy",
                "episode_step": 3,
                "current_email_id": "email_3",
                "emails_processed": [
                    {
                        "email_id": "email_1",
                        "action": "classify",
                        "category": "urgent",
                        "correct": True
                    }
                ],
                "total_correct": 1,
                "total_wrong": 0,
                "cumulative_reward": 0.75
            }
        }
