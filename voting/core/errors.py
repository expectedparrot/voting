from __future__ import annotations


class VotingError(Exception):
    exit_code = 1
    code = "voting_error"

    def __init__(self, message: str, details: dict | None = None, hint: str = ""):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.hint = hint


class ProjectNotFound(VotingError):
    exit_code = 2
    code = "missing_project"

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        hint: str = "Run `voting init <name>` to create a project.",
    ):
        super().__init__(message, details, hint)


class InvalidProject(VotingError):
    exit_code = 2
    code = "invalid_project"

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        hint: str = "Check that .voting/meta.json exists and is valid JSON.",
    ):
        super().__init__(message, details, hint)


class UserError(VotingError):
    exit_code = 1
    code = "user_error"


class ValidationError(VotingError):
    exit_code = 3
    code = "validation_error"


class AnalysisError(VotingError):
    exit_code = 4
    code = "analysis_error"
