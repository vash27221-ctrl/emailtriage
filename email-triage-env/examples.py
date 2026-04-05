"""
Example: How to use the Email Triage Environment

This module demonstrates the complete workflow for interacting with the
EmailTriageEnv, from environment initialization through episode execution.
"""

# ============================================================================
# 1. BASIC ENVIRONMENT SETUP
# ============================================================================

from email_triage.environment import EmailTriageEnv
from email_triage.models import Action, ActionType, EmailCategory

# Initialize for a specific task
env = EmailTriageEnv(task_id="task_1_easy")

# View task information
task_info = env.get_task_info()
print(f"Task: {task_info['description']}")
print(f"Difficulty: {task_info['difficulty']}")
print(f"Total emails: {task_info['total_emails']}")


# ============================================================================
# 2. RUN A COMPLETE EPISODE
# ============================================================================

def run_episode_with_fixed_strategy():
    """Run an episode with a fixed classification strategy."""
    
    # Reset environment
    observation = env.reset()
    
    done = False
    episode_rewards = []
    
    while not done:
        # Current email information
        current_email = observation.current_email
        
        # YOUR AGENT LOGIC HERE
        # For demo, use a simple heuristic
        if "urgent" in current_email.subject.lower():
            predicted_category = EmailCategory.URGENT
        elif current_email.is_reply:
            predicted_category = EmailCategory.FOLLOW_UP
        else:
            predicted_category = EmailCategory.INFORMATIONAL
        
        # Create action
        action = Action(
            action_type=ActionType.CLASSIFY,
            category=predicted_category,
            reason=f"Heuristic: '{current_email.subject[:40]}...'"
        )
        
        # Step environment
        observation, reward, done, info = env.step(action)
        
        # Track reward
        episode_rewards.append(reward.step_reward)
        
        print(
            f"Email {observation.processed_count}/{observation.total_count}: "
            f"Predicted {predicted_category.value}, "
            f"Accuracy: {reward.accuracy:.2%}"
        )
    
    # Episode complete
    final_state = env.state()
    final_grade = env.task.grade()
    
    print(f"\nEpisode Summary:")
    print(f"  Total emails: {final_state.total_correct + final_state.total_wrong}")
    print(f"  Correct: {final_state.total_correct}")
    print(f"  Wrong: {final_state.total_wrong}")
    print(f"  Final Grade: {final_grade:.2f}/1.0")
    
    return final_state, final_grade


# ============================================================================
# 3. ACCESS DETAILED STATE
# ============================================================================

def examine_state_details():
    """Examine the complete state snapshot."""
    
    observation = env.reset()
    
    # Take just one step
    action = Action(
        action_type=ActionType.CLASSIFY,
        category=EmailCategory.URGENT,
        reason="Test"
    )
    observation, reward, done, info = env.step(action)
    
    # Get complete state
    state = env.state()
    
    print("State snapshot:")
    print(f"  Task ID: {state.task_id}")
    print(f"  Episode step: {state.episode_step}")
    print(f"  Current email: {state.current_email_id}")
    print(f"  Total correct: {state.total_correct}")
    print(f"  Total wrong: {state.total_wrong}")
    print(f"  Cumulative reward: {state.cumulative_reward:.2%}")
    
    print("\nEmail history:")
    for record in state.emails_processed:
        print(f"  - {record['email_id']}: {record['action']} → "
              f"{record['category']} (correct: {record['correct']})")
    
    return state


# ============================================================================
# 4. OBSERVATION AND ACTION SPACES
# ============================================================================

def examine_spaces():
    """Examine the environment's action and observation spaces."""
    
    obs_space = env.observation_space
    action_space = env.action_space
    
    print("Observation Space:")
    for key, value in obs_space["properties"].items():
        print(f"  - {key}: {value}")
    
    print("\nAction Space:")
    for key, value in action_space["properties"].items():
        print(f"  - {key}: {value}")


# ============================================================================
# 5. WORKING WITH MULTIPLE TASKS
# ============================================================================

def run_all_tasks_comparison():
    """Run all three tasks and compare performance."""
    
    results = {}
    
    for task_id in ["task_1_easy", "task_2_medium", "task_3_hard"]:
        env = EmailTriageEnv(task_id=task_id)
        observation = env.reset()
        
        done = False
        correct_count = 0
        total_count = 0
        
        while not done:
            # Simple random classification (for demo)
            import random
            predicted = random.choice([
                EmailCategory.SPAM,
                EmailCategory.URGENT,
                EmailCategory.FOLLOW_UP,
                EmailCategory.INFORMATIONAL,
            ])
            
            action = Action(
                action_type=ActionType.CLASSIFY,
                category=predicted,
                reason="Random"
            )
            
            observation, reward, done, info = env.step(action)
            
            if reward.step_reward > 0:
                correct_count += 1
            total_count += 1
        
        final_grade = env.task.grade()
        accuracy = correct_count / total_count if total_count > 0 else 0.0
        
        results[task_id] = {
            "accuracy": accuracy,
            "grade": final_grade,
            "difficulty": env.task.difficulty,
        }
    
    # Compare
    print("Task Comparison (Random Baseline):")
    print("-" * 60)
    print(f"{'Task':15s} {'Difficulty':12s} {'Accuracy':12s} {'Grade':10s}")
    print("-" * 60)
    
    total_grade = 0.0
    for task_id, result in results.items():
        print(
            f"{task_id:15s} {result['difficulty']:12s} "
            f"{result['accuracy']:11.2%}  {result['grade']:9.2f}"
        )
        total_grade += result['grade']
    
    print("-" * 60)
    avg_grade = total_grade / len(results)
    print(f"{'Average':15s} {'':12s} {'':12s} {avg_grade:9.2f}")


# ============================================================================
# 6. CUSTOM AGENT EXAMPLE
# ============================================================================

class SimpleKeywordAgent:
    """Example agent using keyword matching."""
    
    def __init__(self):
        self.email_count = 0
    
    def act(self, observation) -> Action:
        """Classify email based on keywords."""
        
        self.email_count += 1
        
        email = observation.current_email
        subject = email.subject.lower()
        preview = email.preview.lower()
        text = subject + " " + preview
        
        # Keyword-based logic
        if any(w in text for w in ["urgent", "critical", "alert", "emergency"]):
            category = EmailCategory.URGENT
        elif email.is_reply or any(w in text for w in ["re:", "thanks", "confirm"]):
            category = EmailCategory.FOLLOW_UP
        elif any(w in text for w in ["newsletter", "announcement", "update"]):
            category = EmailCategory.INFORMATIONAL
        elif any(w in text for w in ["free", "click", "verify"]):
            category = EmailCategory.SPAM
        else:
            category = EmailCategory.INFORMATIONAL
        
        return Action(
            action_type=ActionType.CLASSIFY,
            category=category,
            reason=f"Keyword match"
        )


def run_with_custom_agent():
    """Run episode with custom agent."""
    
    agent = SimpleKeywordAgent()
    env = EmailTriageEnv(task_id="task_2_medium")
    
    observation = env.reset()
    done = False
    
    while not done:
        action = agent.act(observation)
        observation, reward, done, info = env.step(action)
    
    final_state = env.state()
    final_grade = env.task.grade()
    
    print(f"Custom Agent Results:")
    print(f"  Accuracy: {final_state.cumulative_reward:.2%}")
    print(f"  Grade: {final_grade:.2f}/1.0")


# ============================================================================
# 7. RENDERING AND DEBUGGING
# ============================================================================

def debug_environment():
    """Print environment state for debugging."""
    
    env = EmailTriageEnv(task_id="task_1_easy")
    observation = env.reset()
    
    # Render current state
    rendered = env.render(mode="text")
    print("Environment Render:")
    print(rendered)
    print()
    
    # Take one step
    action = Action(
        action_type=ActionType.CLASSIFY,
        category=EmailCategory.SPAM,
        reason="Testing"
    )
    observation, reward, done, info = env.step(action)
    
    print("After step:")
    print(f"  Reward: {reward.step_reward}")
    print(f"  Accuracy: {reward.accuracy:.2%}")
    print(f"  Done: {done}")
    print(f"  Info: {info}")


# ============================================================================
# MAIN: Run examples
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("Email Triage Environment - Usage Examples")
    print("="*70)
    
    # Uncomment any example to run
    
    # print("\n1. Basic Episode")
    # print("-"*70)
    # run_episode_with_fixed_strategy()
    
    # print("\n2. Examine State")
    # print("-"*70)
    # examine_state_details()
    
    # print("\n3. Spaces Review")
    # print("-"*70)
    # examine_spaces()
    
    # print("\n4. All Tasks Comparison")
    # print("-"*70)
    # run_all_tasks_comparison()
    
    # print("\n5. Custom Agent")
    # print("-"*70)
    # run_with_custom_agent()
    
    # print("\n6. Debug")
    # print("-"*70)
    # debug_environment()
    
    print("\n" + "="*70)
    print("Uncomment examples in main() to run them")
    print("="*70)
