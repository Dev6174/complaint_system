# pyrefly: ignore [missing-import]
import csv
import io
from typing import List, Any
from sqlalchemy.orm import Session
from app.models import Issue, Feedback, User

def generate_issues_csv(issues: List[Issue]) -> str:
    """
    Generates a CSV string representing the list of issues.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Issue ID", "Reporter ID", "Title", "Category", "Priority", 
        "Latitude", "Longitude", "Status", "Verification Count", 
        "Assigned Department", "Resolved At", "Created At"
    ])
    
    for issue in issues:
        writer.writerow([
            issue.id,
            issue.reporter_id,
            issue.title,
            issue.category,
            issue.priority,
            issue.latitude,
            issue.longitude,
            issue.status,
            issue.verification_count,
            issue.assigned_department or "None",
            issue.resolved_at.isoformat() if issue.resolved_at else "None",
            issue.created_at.isoformat()
        ])
        
    return output.getvalue()

def generate_department_csv(stats: List[dict]) -> str:
    """
    Generates CSV string for department performance summaries.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["Department", "Total Issues", "Resolved Issues", "Pending Issues", "Average Rating"])
    
    for row in stats:
        writer.writerow([
            row.get("department"),
            row.get("total"),
            row.get("resolved"),
            row.get("pending"),
            f"{row.get('avg_rating', 0.0):.2f}"
        ])
        
    return output.getvalue()

def generate_feedback_csv(feedbacks: List[Feedback]) -> str:
    """
    Generates CSV string for community feedback comments and ratings.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["Feedback ID", "Issue ID", "User ID", "Rating", "Comment", "Created At"])
    
    for fb in feedbacks:
        writer.writerow([
            fb.id,
            fb.issue_id,
            fb.user_id,
            fb.rating,
            fb.comment or "",
            fb.created_at.isoformat()
        ])
        
    return output.getvalue()
