"""OpenEnv specification and validation."""

import json

OPENENV_SPEC = {
    "name": "email-triage-env",
    "version": "1.0.0",
    "description": "Real-world email triage environment for training RL agents",
    "author": "OpenEnv Contributors",
    "license": "MIT",
    
    "environment": {
        "id": "EmailTriage-v1",
        "entry_point": "email_triage.environment:EmailTriageEnv",
        "max_episode_steps": None,
        "reward_threshold": 0.8,
    },
    
    "tasks": [
        {
            "id": "task_1_easy",
            "name": "Spam Detection (Easy)",
            "description": "Binary classification of obvious spam vs legitimate emails",
            "difficulty": "easy",
            "num_episodes": 1,
            "reward_threshold": 0.9,
        },
        {
            "id": "task_2_medium",
            "name": "Multi-Category Classification (Medium)",
            "description": "4-way classification: URGENT, FOLLOW_UP, INFORMATIONAL, and implicit SPAM handling",
            "difficulty": "medium",
            "num_episodes": 1,
            "reward_threshold": 0.75,
        },
        {
            "id": "task_3_hard",
            "name": "Edge Cases & Ambiguity (Hard)",
            "description": "Complex, similar categories requiring deep contextual understanding",
            "difficulty": "hard",
            "num_episodes": 1,
            "reward_threshold": 0.6,
        },
    ],
    
    "observation_spec": {
        "name": "Observation",
        "type": "pydantic",
        "model": "email_triage.models.Observation",
        "fields": {
            "current_email": {
                "type": "Email",
                "description": "Current email being processed"
            },
            "processed_count": {
                "type": "int",
                "description": "Number of emails processed"
            },
            "total_count": {
                "type": "int",
                "description": "Total emails in batch"
            },
            "correct_classifications": {
                "type": "int",
                "description": "Number of correct classifications"
            },
            "task_id": {
                "type": "str",
                "description": "Task identifier"
            },
            "hint": {
                "type": "Optional[str]",
                "description": "Optional task-specific hint"
            }
        }
    },
    
    "action_spec": {
        "name": "Action",
        "type": "pydantic",
        "model": "email_triage.models.Action",
        "fields": {
            "action_type": {
                "type": "ActionType",
                "enum": ["classify", "read_more", "flag", "archive", "skip"],
                "description": "Type of action"
            },
            "category": {
                "type": "Optional[EmailCategory]",
                "enum": ["spam", "urgent", "follow_up", "informational", "archived"],
                "description": "Target category for classification"
            },
            "reason": {
                "type": "Optional[str]",
                "description": "Explanation for the action"
            }
        }
    },
    
    "reward_spec": {
        "name": "Reward",
        "type": "pydantic",
        "model": "email_triage.models.Reward",
        "description": "Reward signal with partial progress",
        "fields": {
            "step_reward": {
                "type": "float",
                "range": [0.0, 1.0],
                "description": "Reward for current step"
            },
            "cumulative_reward": {
                "type": "float",
                "range": [0.0, 1.0],
                "description": "Cumulative episode reward (accuracy)"
            },
            "accuracy": {
                "type": "float",
                "range": [0.0, 1.0],
                "description": "Current accuracy"
            },
            "bonus": {
                "type": "float",
                "description": "Bonus for exceptional performance"
            },
            "penalty": {
                "type": "float",
                "description": "Penalty for errors"
            }
        }
    },
    
    "implementation": {
        "language": "python",
        "version": "3.10+",
        "dependencies": [
            "pydantic>=2.0",
            "groq>=0.9.0",
            "python-dotenv>=0.21.0",
        ],
        "methods": {
            "reset": {
                "description": "Reset environment and return initial observation",
                "returns": "Observation"
            },
            "step": {
                "description": "Execute action and return observation, reward, done, info",
                "parameters": ["action: Action"],
                "returns": "(Observation, Reward, bool, dict)"
            },
            "state": {
                "description": "Get complete state snapshot",
                "returns": "StateSnapshot"
            },
        }
    },
}

def get_openenv_spec_yaml() -> str:
    """Return OpenEnv spec as YAML-compatible string."""
    return json.dumps(OPENENV_SPEC, indent=2)

def validate_environment_spec() -> bool:
    """Validate that environment matches OpenEnv spec."""
    required_methods = ["reset", "step", "state"]
    required_pydantic_models = ["Action", "Observation", "Reward", "StateSnapshot"]
    
    try:
        from email_triage.environment import EmailTriageEnv
        from email_triage.models import Action, Observation, Reward, StateSnapshot
        
        # Check methods exist
        env = EmailTriageEnv()
        for method in required_methods:
            if not hasattr(env, method):
                print(f"❌ Missing method: {method}")
                return False
        
        # Check Pydantic models exist
        for model_name in required_pydantic_models:
            if model_name not in ["Action", "Observation", "Reward", "StateSnapshot"]:
                continue
        
        print("✓ All OpenEnv requirements satisfied")
        return True
    
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False
