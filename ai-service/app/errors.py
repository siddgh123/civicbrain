"""Typed exceptions of the AI service (docs/12_ERROR_HANDLING.md sec. 7).

A failed job is finished with fn_finish_job(id, false, '<ExceptionType>: <message>'), so the class name is
what the admin jobs page shows. ConfigError stops the worker at start-up instead of failing jobs one by one.
"""


class CivicBrainError(Exception):
    """Base class of every expected AI-service error."""


class ConfigError(CivicBrainError):
    """A setting or a required model file / checksum is missing or invalid."""


class ModelError(CivicBrainError):
    """A model is not available or failed while running."""


class DataError(CivicBrainError):
    """Input data (complaint, image, job row) is missing or invalid."""


class DependencyError(CivicBrainError):
    """An external dependency (database, storage, OSRM) is unavailable."""


class JobTimeoutError(CivicBrainError):
    """A job ran longer than its hard limit (docs/06_AI_PIPELINE.md sec. 1)."""
