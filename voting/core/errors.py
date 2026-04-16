from __future__ import annotations


class VotingError(Exception):
    exit_code = 1
    code = "voting_error"

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ProjectNotFound(VotingError):
    exit_code = 2
    code = "missing_project"


class InvalidProject(VotingError):
    exit_code = 2
    code = "invalid_project"


class UserError(VotingError):
    exit_code = 1
    code = "user_error"


class ValidationError(VotingError):
    exit_code = 3
    code = "validation_error"


class AnalysisError(VotingError):
    exit_code = 4
    code = "analysis_error"
