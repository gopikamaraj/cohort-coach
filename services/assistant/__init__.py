"""One assistant, scoped by role (docs/build/reports/ASSISTANT.md).

The scope is set on the server from the authenticated role and nothing else (scopes.py). Answers
come only from the role's namespaces (retrieve.py), every one cites its sources (answer.py), and the
assistant is read-only: it never approves, sends or deletes.
"""
