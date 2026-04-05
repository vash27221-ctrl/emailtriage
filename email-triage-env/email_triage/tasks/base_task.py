"""Base task class for email triage."""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from email_triage.models import Email, EmailCategory, Observation, Reward


class Task(ABC):
    """Abstract base task."""

    def __init__(self, task_id: str, description: str, difficulty: str):
        self.task_id = task_id
        self.description = description
        self.difficulty = difficulty  # "easy", "medium", "hard"
        self.emails: List[Email] = []
        self.current_email_idx = 0
        self.actions_taken: List[Tuple[str, str]] = []  # (email_id, category)
        self.correct_count = 0
        self.total_processed = 0

    @abstractmethod
    def generate_emails(self) -> List[Email]:
        """Generate task-specific email batch."""
        pass

    def reset(self) -> Observation:
        """Reset task and return initial observation."""
        self.emails = self.generate_emails()
        self.current_email_idx = 0
        self.actions_taken = []
        self.correct_count = 0
        self.total_processed = 0
        return self._get_observation()

    def _get_observation(self) -> Observation:
        """Get current observation."""
        email = self.emails[self.current_email_idx]
        email_display = email.copy(deep=True)
        # Hide ground truth from observation
        email_display.ground_truth_category = None
        
        return Observation(
            current_email=email,
            processed_count=self.current_email_idx,
            total_count=len(self.emails),
            correct_classifications=self.correct_count,
            task_id=self.task_id,
            hint=self._get_hint()
        )

    def _get_hint(self) -> Optional[str]:
        """Return task-specific hint (can be overridden)."""
        return None

    def step(self, predicted_category: EmailCategory) -> Tuple[Observation, Reward, bool]:
        """
        Process one action.
        
        Returns:
            observation: Next observation
            reward: Reward signal
            done: Whether episode is complete
        """
        current_email = self.emails[self.current_email_idx]
        self.total_processed += 1
        
        is_correct = predicted_category == current_email.ground_truth_category
        if is_correct:
            self.correct_count += 1
        
        self.actions_taken.append((current_email.id, predicted_category))
        
        # Calculate reward
        reward = self._calculate_reward(is_correct)
        
        # Move to next email or mark done
        self.current_email_idx += 1
        done = self.current_email_idx >= len(self.emails)
        
        if done:
            next_obs = self._get_final_observation()
        else:
            next_obs = self._get_observation()
        
        return next_obs, reward, done

    def _calculate_reward(self, is_correct: bool) -> Reward:
        """Calculate reward for this step."""
        step_reward = 1.0 if is_correct else 0.0
        cumulative = self.correct_count / self.total_processed if self.total_processed > 0 else 0.0
        
        return Reward(
            step_reward=step_reward,
            cumulative_reward=cumulative,
            accuracy=cumulative,
            bonus=0.0,
            penalty=0.0 if is_correct else 0.1
        )

    def _get_final_observation(self) -> Observation:
        """Get final observation when episode ends."""
        # Return a dummy email or last email info
        email = self.emails[-1]
        email_display = email.copy(deep=True)
        
        return Observation(
            current_email=email_display,
            processed_count=len(self.emails),
            total_count=len(self.emails),
            correct_classifications=self.correct_count,
            task_id=self.task_id,
            hint="Episode complete"
        )

    @abstractmethod
    def grade(self) -> float:
        """
        Grade the task performance (0.0-1.0).
        Deterministic grader based on accuracy and performance metrics.
        """
        pass

    def get_performance_metrics(self) -> dict:
        """Return detailed performance metrics."""
        accuracy = self.correct_count / self.total_processed if self.total_processed > 0 else 0.0
        return {
            "accuracy": accuracy,
            "correct": self.correct_count,
            "total": self.total_processed,
            "task_id": self.task_id,
            "difficulty": self.difficulty
        }
