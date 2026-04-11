"""Main OpenEnv Environment implementing the full interface."""

from typing import Optional, Tuple, Dict, Any
from email_triage.models import (
    Observation,
    Action,
    ActionType,
    EmailCategory,
    Reward,
    StateSnapshot,
)
from email_triage.tasks import AVAILABLE_TASKS
from email_triage.tasks.base_task import Task


class EmailTriageEnv:
    """
    Email Triage OpenEnv Environment.
    
    Real-world task: Classify incoming emails to improve inbox management
    and ensure important messages aren't missed.
    
    Agents must:
    1. Read emails with subject, sender, and preview
    2. Classify into: SPAM, URGENT, FOLLOW_UP, INFORMATIONAL, ARCHIVED
    3. Achieve high accuracy across 3 difficulty levels
    
    Tasks:
    - Easy: Binary spam detection (obvious signals)
    - Medium: 4-class classification with mixed difficulty
    - Hard: Edge cases and ambiguous emails
    """
    
    def __init__(self, task_id: str = "task_1_easy"):
        """Initialize environment for specific task."""
        if task_id not in AVAILABLE_TASKS:
            raise ValueError(
                f"Unknown task: {task_id}. "
                f"Available: {list(AVAILABLE_TASKS.keys())}"
            )
        
        self.task_id = task_id
        self.task: Optional[Task] = None
        self._init_task()
        self._episode_step = 0
        self._history = []

    def _init_task(self):
        """Initialize the task."""
        task_class = AVAILABLE_TASKS[self.task_id]
        self.task = task_class()

    def reset(self) -> Observation:
        """
        Reset environment and start new episode.
        
        Returns:
            Initial observation of the environment
        """
        self.task.reset()
        self._episode_step = 0
        self._history = []
        return self.task._get_observation()

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        """
        Execute one action and return results.
        
        Args:
            action: Agent's action (classification or other action)
        
        Returns:
            observation: Next observation
            reward: Reward signal
            done: Whether episode ended
            info: Additional metadata
        """
        if action.action_type != ActionType.CLASSIFY:
            # Handle non-classification actions
            return self._handle_special_action(action)
        
        if action.category is None:
            raise ValueError("CLASSIFY action requires a category")
        
        # Execute classification
        current_email = self.task.emails[self.task.current_email_idx]
        observation, reward, done = self.task.step(action.category)
        
        self._episode_step += 1
        
        # Log history
        self._history.append({
            "step": self._episode_step,
            "email_id": current_email.id,
            "predicted": action.category,
            "ground_truth": current_email.ground_truth_category,
            "correct": action.category == current_email.ground_truth_category,
            "reason": action.reason,
        })
        
        info = {
            "step": self._episode_step,
            "task_id": self.task_id,
            "email_id": current_email.id,
            "action_type": action.action_type,
        }
        
        if done:
            # Calculate final grade
            final_grade = self.task.grade()
            info["final_grade"] = final_grade
            info["performance"] = self.task.get_performance_metrics()
        
        return observation, reward, done, info

    def _handle_special_action(
        self, action: Action
    ) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        """Handle non-CLASSIFY actions (READ_MORE, FLAG, SKIP, ARCHIVE)."""
        # For now, treat all special actions as penalty
        current_email = self.task.emails[self.task.current_email_idx]
        
        # Skip or archive = treat as abstention, small penalty
        if action.action_type in [ActionType.SKIP, ActionType.ARCHIVE]:
            # Count as wrong classification
            observation, reward, done = self.task.step(EmailCategory.ARCHIVED)
        else:
            # READ_MORE, FLAG = no step, just observation
            observation = self.task._get_observation()
            done = False
            reward = Reward(
                step_reward=0.01,
                cumulative_reward=max(0.01, min(0.99, self.task.correct_count / max(self.task.total_processed, 1))),
                accuracy=max(0.01, min(0.99, self.task.correct_count / max(self.task.total_processed, 1))),
            )
        
        info = {
            "action_type": action.action_type,
            "reason": action.reason,
        }
        
        return observation, reward, done, info

    def state(self) -> StateSnapshot:
        """
        Get complete environment state snapshot.
        
        Returns:
            Complete state information for saving/loading
        """
        return StateSnapshot(
            task_id=self.task_id,
            episode_step=self._episode_step,
            current_email_id=self.task.emails[self.task.current_email_idx].id
            if self.task.current_email_idx < len(self.task.emails)
            else "",
            emails_processed=self._history,
            total_correct=self.task.correct_count,
            total_wrong=self.task.total_processed - self.task.correct_count,
            cumulative_reward=max(0.01, min(0.99, self.task.correct_count / max(self.task.total_processed, 1))),
        )

    def get_task_info(self) -> Dict[str, Any]:
        """Get metadata about current task."""
        return {
            "task_id": self.task_id,
            "description": self.task.description,
            "difficulty": self.task.difficulty,
            "total_emails": len(self.task.emails),
        }

    def render(self, mode: str = "text") -> str:
        """Render environment state (for debugging)."""
        if self.task.current_email_idx >= len(self.task.emails):
            return "Episode complete"
        
        email = self.task.emails[self.task.current_email_idx]
        
        output = [
            f"Task: {self.task_id} ({self.task.difficulty})",
            f"Step: {self._episode_step + 1}/{len(self.task.emails)}",
            f"Correct: {self.task.correct_count}/{self.task.total_processed}",
            "",
            f"From: {email.sender}",
            f"Subject: {email.subject}",
            f"Preview: {email.preview[:100]}...",
            f"Reply: {email.is_reply}, Attachment: {email.has_attachment}",
        ]
        
        return "\n".join(output)

    @property
    def observation_space(self) -> Dict[str, Any]:
        """Return observation space definition."""
        return {
            "type": "Observation",
            "properties": {
                "current_email": {
                    "type": "Email",
                    "properties": {
                        "id": "str",
                        "sender": "str",
                        "subject": "str",
                        "preview": "str",
                        "received_time": "str (ISO format)",
                        "is_reply": "bool",
                        "has_attachment": "bool",
                    }
                },
                "processed_count": "int",
                "total_count": "int",
                "correct_classifications": "int",
                "task_id": "str",
                "hint": "Optional[str]",
            }
        }

    @property
    def action_space(self) -> Dict[str, Any]:
        """Return action space definition."""
        return {
            "type": "Action",
            "properties": {
                "action_type": {
                    "type": "ActionType (enum)",
                    "values": ["classify", "read_more", "flag", "archive", "skip"]
                },
                "category": {
                    "type": "Optional[EmailCategory (enum)]",
                    "values": ["spam", "urgent", "follow_up", "informational", "archived"],
                    "required_for": ["classify"]
                },
                "reason": "Optional[str]",
            }
        }
