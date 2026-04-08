"""Task implementations: Easy, Medium, Hard"""

from typing import List
from datetime import datetime, timedelta
import random
from email_triage.models import Email, EmailCategory
from email_triage.tasks.base_task import Task


class EasySpamDetectionTask(Task):
    """
    Easy Task: Binary spam vs not-spam detection.
    Emails have obvious spam indicators (phishing attempts, generic viagra ads).
    Grading: Must achieve 90%+ accuracy to pass.
    """

    def __init__(self):
        super().__init__(
            task_id="task_1_easy",
            description="Detect obvious spam emails",
            difficulty="easy"
        )

    def generate_emails(self) -> List[Email]:
        """Generate obvious spam and legitimate emails."""
        emails = []
        
        spam_subjects = [
            "YOU HAVE WON! Claim your prize now!!!",
            "Buy Viagra - 50% OFF NOW",
            "URGENT: Verify your bank account immediately",
            "Click here to receive FREE MONEY",
            "Your account has been compromised - CLICK IMMEDIATELY",
        ]
        
        spam_previews = [
            "Congratulations! You have won a free prize. Click here to claim it now...",
            "Cheap medications! Viagra, cialis, and more. Order now and save 50%...",
            "Your account security has been compromised. Please click here to verify...",
            "Free money waiting for you! No strings attached. Claim now...",
            "Your login failed. Update your password immediately to restore access...",
        ]
        
        legitimate_subjects = [
            "Project Alpha: Q1 Status Update",
            "Team Lunch Tomorrow at Noon",
            "Customer Request: Database Migration Timeline",
            "Meeting Notes: Sprint Planning",
            "Budget Review - Finance Department",
            "Code Review: Pull Request #456",
        ]
        
        legitimate_previews = [
            "Please find attached the Q1 status report for Project Alpha...",
            "Hi team, don't forget about our team lunch tomorrow at noon...",
            "The customer needs a timeline for the database migration project...",
            "Here are the notes from today's sprint planning meeting...",
            "Please review the attached budget proposal for the upcoming quarter...",
            "I've created a pull request that needs your review before merging...",
        ]

        # Fixed ground truth labels — consistent across episodes so the agent can learn
        legitimate_categories = [
            EmailCategory.INFORMATIONAL,  # Q1 status update — FYI report
            EmailCategory.INFORMATIONAL,  # Team lunch — announcement
            EmailCategory.FOLLOW_UP,      # Customer request — needs response
            EmailCategory.INFORMATIONAL,  # Meeting notes — FYI
            EmailCategory.FOLLOW_UP,      # Budget review — needs approval
            EmailCategory.FOLLOW_UP,      # Code review — needs your review
        ]
        
        base_time = datetime.now()
        idx = 0
        
        # Add spam emails
        for i, subject in enumerate(spam_subjects):
            emails.append(Email(
                id=f"email_{idx}",
                sender=f"spammer{i}@suspicious-domain.com",
                subject=subject,
                preview=spam_previews[i],
                received_time=(base_time - timedelta(hours=i)).isoformat() + "Z",
                is_reply=False,
                has_attachment=False,
                ground_truth_category=EmailCategory.SPAM
            ))
            idx += 1
        
        # Add legitimate emails
        for i, subject in enumerate(legitimate_subjects):
            emails.append(Email(
                id=f"email_{idx}",
                sender=f"colleague{i}@company.com",
                subject=subject,
                preview=legitimate_previews[i],
                received_time=(base_time - timedelta(hours=5+i)).isoformat() + "Z",
                is_reply=random.choice([True, False]),
                has_attachment=random.choice([True, False]),
                ground_truth_category=legitimate_categories[i]
            ))
            idx += 1
        
        random.shuffle(emails)
        return emails

    def _get_hint(self) -> str:
        """Provide hint for easy task."""
        email = self.emails[self.current_email_idx]
        if email.ground_truth_category == EmailCategory.SPAM:
            indicators = []
            if "!!!" in email.subject or "FREE" in email.subject or "WON" in email.subject:
                indicators.append("excessive punctuation or all-caps")
            if "@suspicious" in email.sender or "@mail-temp" in email.sender:
                indicators.append("suspicious sender domain")
            if any(word in email.subject.lower() for word in ["viagra", "money", "claim", "win"]):
                indicators.append("common spam keywords")
            
            if indicators:
                return f"Notice: {', '.join(indicators)}"
        
        return "Look for legitimate professional indicators (company domain, clear purpose)"

    def grade(self) -> float:
        """
        Grading: 
        - 90%+ accuracy: 1.0
        - 70-89%: 0.6
        - Below 70%: 0.0 (failure)
        """
        if self.total_processed == 0:
            return 0.0
        
        accuracy = self.correct_count / self.total_processed
        
        if accuracy >= 0.90:
            return 1.0
        elif accuracy >= 0.70:
            return 0.6
        else:
            return 0.0


class MediumMultiClassificationTask(Task):
    """
    Medium Task: Multi-category classification (4 categories).
    Mix of obvious and ambiguous emails requiring reasoning.
    Grading: Accuracy-based with partial credit.
    """

    def __init__(self):
        super().__init__(
            task_id="task_2_medium",
            description="Classify emails into 4 categories with mixed signals",
            difficulty="medium"
        )

    def generate_emails(self) -> List[Email]:
        """Generate mixed-difficulty emails."""
        emails = []
        base_time = datetime.now()
        
        # Urgent emails
        urgent_data = [
            ("CRITICAL: Production Outage Alert", "Our production database is down. Immediate action required..."),
            ("Security Alert: Unauthorized Login Attempt", "Someone tried to access your account from a new location..."),
            ("Emergency: Client Issues - Response Needed ASAP", "Major client reporting critical issues with our service..."),
        ]
        
        # Follow-up needed
        followup_data = [
            ("Re: Your proposal feedback request", "Thanks for sending that. We discussed it in the team..."),
            ("Waiting for your input on architecture", "The team is waiting for your decision on the tech stack..."),
            ("Action needed: Approve budget allocation", "This budget request needs your approval to proceed..."),
        ]
        
        # Informational
        info_data = [
            ("Weekly Company Newsletter - April 2026", "This week's highlights: new features launched, team updates..."),
            ("System Maintenance Scheduled for Sunday", "Planned maintenance window: Sunday 2-4 AM UTC..."),
            ("Q1 Results: Great quarter for our team!", "Sales exceeded targets by 15%, customer satisfaction up..."),
        ]
        
        idx = 0
        for subject, preview in urgent_data:
            emails.append(Email(
                id=f"email_{idx}",
                sender="alerts@company.com",
                subject=subject,
                preview=preview,
                received_time=(base_time - timedelta(hours=idx)).isoformat() + "Z",
                is_reply=False,
                has_attachment=False,
                ground_truth_category=EmailCategory.URGENT
            ))
            idx += 1
        
        for subject, preview in followup_data:
            emails.append(Email(
                id=f"email_{idx}",
                sender=f"colleague{idx}@company.com",
                subject=subject,
                preview=preview,
                received_time=(base_time - timedelta(hours=idx)).isoformat() + "Z",
                is_reply=True,
                has_attachment=False,
                ground_truth_category=EmailCategory.FOLLOW_UP
            ))
            idx += 1
        
        for subject, preview in info_data:
            emails.append(Email(
                id=f"email_{idx}",
                sender="noreply@company.com",
                subject=subject,
                preview=preview,
                received_time=(base_time - timedelta(hours=idx)).isoformat() + "Z",
                is_reply=False,
                has_attachment=False,
                ground_truth_category=EmailCategory.INFORMATIONAL
            ))
            idx += 1
        
        # Add some ambiguous emails
        ambiguous = [
            ("Re: Meeting tomorrow at 3 PM?", "Just confirming - are we still meeting tomorrow?", EmailCategory.FOLLOW_UP),
            ("New feature announcement", "Check out our latest feature in the admin console...", EmailCategory.INFORMATIONAL),
            ("Action: Please fill out survey", "We need your feedback on office tools, please respond...", EmailCategory.FOLLOW_UP),
        ]
        
        for subject, preview, category in ambiguous:
            emails.append(Email(
                id=f"email_{idx}",
                sender=f"sender{idx}@company.com",
                subject=subject,
                preview=preview,
                received_time=(base_time - timedelta(hours=idx)).isoformat() + "Z",
                is_reply=random.choice([True, False]),
                has_attachment=random.choice([True, False]),
                ground_truth_category=category
            ))
            idx += 1
        
        random.shuffle(emails)
        return emails

    def _get_hint(self) -> str:
        """Provide strategy hint."""
        email = self.emails[self.current_email_idx]
        
        hints = {
            EmailCategory.URGENT: "Look for keywords like CRITICAL, ALERT, immediate, ASAP, emergency",
            EmailCategory.FOLLOW_UP: "Check if it's a reply, asks for input, or awaits decision",
            EmailCategory.INFORMATIONAL: "Newsletters, announcements, updates - no action items",
            EmailCategory.SPAM: "Suspicious sender, phishing attempts, malware links",
        }
        
        return hints.get(email.ground_truth_category, "Consider the sender, subject, and urgency indicators")

    def grade(self) -> float:
        """
        Grading:
        - 85%+ accuracy: 1.0
        - 70-84%: 0.75
        - 60-69%: 0.5
        - Below 60%: 0.25
        """
        if self.total_processed == 0:
            return 0.0
        
        accuracy = self.correct_count / self.total_processed
        
        if accuracy >= 0.85:
            return 1.0
        elif accuracy >= 0.70:
            return 0.75
        elif accuracy >= 0.60:
            return 0.5
        else:
            return 0.25


class HardEdgeCaseTask(Task):
    """
    Hard Task: Complex edge cases with similar categories, adversarial examples.
    Requires deep understanding to distinguish between similar categories.
    Grading: Strict accuracy requirements with bonus for perfect score.
    """

    def __init__(self):
        super().__init__(
            task_id="task_3_hard",
            description="Handle complex edge cases and ambiguous classifications",
            difficulty="hard"
        )

    def generate_emails(self) -> List[Email]:
        """Generate challenging, ambiguous emails."""
        emails = []
        base_time = datetime.now()
        idx = 0
        
        # Hard edge cases
        hard_cases = [
            ("Re: Fix bug before release", "We found critical issues. We need fixes ASAP before shipping...", EmailCategory.URGENT),
            ("Friendly reminder: Q2 planning session tomorrow", "Just a heads up - everyone's meeting at 2 PM tomorrow...", EmailCategory.FOLLOW_UP),
            ("Performance metrics report for April", "Here's the monthly performance report attached...", EmailCategory.INFORMATIONAL),
            ("HELP: Database connection failing", "Our integration is broken, production is affected!", EmailCategory.URGENT),
            ("Thanks for the review feedback", "Appreciate your comments, will incorporate changes soon...", EmailCategory.FOLLOW_UP),
            ("Congrats on the promotion!", "Excited to see you in your new role!", EmailCategory.INFORMATIONAL),
            ("System degraded - investigating", "Alert: Slow response times detected, our team is investigating...", EmailCategory.URGENT),
            ("Follow up: Did you see my email?", "Just checking if you got my previous message about the proposal...", EmailCategory.FOLLOW_UP),
            ("Blog post: Best practices for DevOps", "Read about modern DevOps practices in our new article...", EmailCategory.INFORMATIONAL),
            ("BREAKING: We have a critical data leak", "Security incident: possible unauthorized access detected...", EmailCategory.URGENT),
        ]
        
        for subject, preview, category in hard_cases:
            emails.append(Email(
                id=f"email_{idx}",
                sender=f"contact{idx}@company.com" if idx % 2 == 0 else f"alert@company.com",
                subject=subject,
                preview=preview,
                received_time=(base_time - timedelta(hours=idx)).isoformat() + "Z",
                is_reply=bool(subject.startswith("Re:")),
                has_attachment=False,
                ground_truth_category=category
            ))
            idx += 1
        
        random.shuffle(emails)
        return emails

    def _get_hint(self) -> str:
        """Provide sophisticated hints."""
        email = self.emails[self.current_email_idx]
        
        # Analyze contextual clues instead of just keywords
        context_clues = []
        
        if "critical" in email.subject.lower() or "emergency" in email.subject.lower():
            context_clues.append("severity indicators suggest URGENT")
        
        if email.is_reply or "re:" in email.subject.lower():
            context_clues.append("could be FOLLOW_UP (is a reply)")
        
        if any(word in email.subject.lower() for word in ["report", "newsletter", "update", "blog", "article"]):
            context_clues.append("likely INFORMATIONAL (educational/reporting)")
        
        if "action needed" in email.preview.lower() or "awaiting" in email.preview.lower():
            context_clues.append("someone might be waiting for you (FOLLOW_UP)")
        
        return " | ".join(context_clues) if context_clues else "Complex decision - analyze context carefully"

    def grade(self) -> float:
        """
        Strict grading with bonus:
        - 90%+ accuracy: 1.0 (excellent)
        - 80-89%: 0.8
        - 70-79%: 0.6
        - 60-69%: 0.3
        - Below 60%: 0.0
        """
        if self.total_processed == 0:
            return 0.0
        
        accuracy = self.correct_count / self.total_processed
        
        if accuracy >= 0.90:
            return 1.0
        elif accuracy >= 0.80:
            return 0.8
        elif accuracy >= 0.70:
            return 0.6
        elif accuracy >= 0.60:
            return 0.3
        else:
            return 0.0
