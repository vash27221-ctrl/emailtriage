#!/usr/bin/env python
"""Test script to validate environment setup."""

import sys


def test_imports():
    """Test that all modules import correctly."""
    print("Testing imports...")
    try:
        from email_triage.environment import EmailTriageEnv
        from email_triage.models import (
            Observation, Action, Reward, StateSnapshot,
            ActionType, EmailCategory
        )
        from email_triage.tasks import AVAILABLE_TASKS
        from email_triage.openenv_spec import validate_environment_spec
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_environment_creation():
    """Test environment initialization."""
    print("\nTesting environment creation...")
    try:
        from email_triage.environment import EmailTriageEnv
        
        for task_id in ["task_1_easy", "task_2_medium", "task_3_hard"]:
            env = EmailTriageEnv(task_id=task_id)
            print(f"✓ Created {task_id}")
        
        return True
    except Exception as e:
        print(f"✗ Environment creation failed: {e}")
        return False


def test_episode():
    """Test a short episode."""
    print("\nTesting episode execution...")
    try:
        from email_triage.environment import EmailTriageEnv
        from email_triage.models import Action, ActionType, EmailCategory
        
        env = EmailTriageEnv(task_id="task_1_easy")
        obs = env.reset()
        
        # Take 3 steps
        for i in range(3):
            action = Action(
                action_type=ActionType.CLASSIFY,
                category=EmailCategory.INFORMATIONAL,
                reason="Test classification"
            )
            obs, reward, done, info = env.step(action)
            print(f"  Step {i+1}: Reward {reward.step_reward:.1f}, "
                  f"Accuracy {reward.accuracy:.2%}")
            if done:
                print(f"  Episode ended early at step {i+1}")
                break
        
        print("✓ Episode execution successful")
        return True
    except Exception as e:
        print(f"✗ Episode execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graders():
    """Test that graders work."""
    print("\nTesting task graders...")
    try:
        from email_triage.environment import EmailTriageEnv
        from email_triage.models import Action, ActionType, EmailCategory
        
        for task_id in ["task_1_easy", "task_2_medium", "task_3_hard"]:
            env = EmailTriageEnv(task_id=task_id)
            obs = env.reset()
            
            # Run full episode
            done = False
            while not done:
                action = Action(
                    action_type=ActionType.CLASSIFY,
                    category=EmailCategory.URGENT,
                    reason="Test"
                )
                obs, reward, done, info = env.step(action)
            
            grade = env.task.grade()
            print(f"✓ {task_id}: Grade={grade:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ Grader test failed: {e}")
        return False


def test_openenv_spec():
    """Test OpenEnv specification validation."""
    print("\nTesting OpenEnv specification...")
    try:
        from email_triage.openenv_spec import validate_environment_spec
        is_valid = validate_environment_spec()
        if is_valid:
            print("✓ OpenEnv specification is valid")
            return True
        else:
            print("✗ OpenEnv specification validation returned False")
            return False
    except Exception as e:
        print(f"✗ OpenEnv spec test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("Email Triage Environment - Test Suite")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Environment Creation", test_environment_creation),
        ("Episode Execution", test_episode),
        ("Task Graders", test_graders),
        ("OpenEnv Spec", test_openenv_spec),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:7s} {name}")
    
    print("="*60)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
