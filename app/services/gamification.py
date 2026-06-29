# pyrefly: ignore [missing-import]
import json

from sqlalchemy.orm import Session

from app.models import User

# Point awards definitions
POINTS_RULES = {
    "report_issue": 10,
    "verify_issue": 2,
    "submit_feedback": 5,
    "issue_resolved_bonus": 15,
}

BADGES_RULES = {
    "First Report": "Awarded for reporting your first issue.",
    "Community Pillar": "Awarded for verifying your first issue.",
    "Civic Voice": "Awarded for providing feedback on a resolved issue.",
    "Super Citizen": "Awarded for achieving 100 or more activity points."
}

def award_points(db: Session, user: User, action_type: str) -> list[str]:
    """
    Awards points to the user and checks for badge eligibility.
    Returns list of newly unlocked badge names.
    """
    points_to_add = POINTS_RULES.get(action_type, 0)
    if points_to_add == 0:
        return []

    user.points += points_to_add

    # Load current badges
    try:
        current_badges = json.loads(user.badges)
    except Exception:
        current_badges = []

    newly_unlocked = []

    # Check "First Report" badge
    if action_type == "report_issue" and "First Report" not in current_badges:
        current_badges.append("First Report")
        newly_unlocked.append("First Report")

    # Check "Community Pillar" badge
    if action_type == "verify_issue" and "Community Pillar" not in current_badges:
        current_badges.append("Community Pillar")
        newly_unlocked.append("Community Pillar")

    # Check "Civic Voice" badge
    if action_type == "submit_feedback" and "Civic Voice" not in current_badges:
        current_badges.append("Civic Voice")
        newly_unlocked.append("Civic Voice")

    # Check "Super Citizen" badge
    if user.points >= 100 and "Super Citizen" not in current_badges:
        current_badges.append("Super Citizen")
        newly_unlocked.append("Super Citizen")

    user.badges = json.dumps(current_badges)
    db.commit()
    return newly_unlocked
