"""Prompt templates loaded at runtime by workspaces.

Each .txt file is read once at workspace creation and merged into every chat
request. The Socratic defaults live in the file bodies; Python defaults in
`INF03Workspace._socratic_prompt` are only used when the file is missing
(e.g. in early CI smoke tests).
"""