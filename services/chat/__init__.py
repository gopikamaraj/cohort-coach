"""The cohort Q&A chat: a teacher asks her mentor; the AI may draft a reply from approved material.

Every step is code around two model calls (12 classifies, 13 drafts). Nothing the AI drafted
reaches a teacher unless a person sent it, or every auto-send gate passed (services/chat/scheduler).
"""
