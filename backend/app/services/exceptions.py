"""Service-layer errors.

These are plain Python exceptions on purpose. The service layer must not know
that FastAPI exists, so it never raises HTTPException - the API layer catches
these and decides which HTTP status each one deserves.
"""


class ResumeServiceError(Exception):
    """Base class so the API layer can catch every service error with one except."""


class UnsupportedFileTypeError(ResumeServiceError):
    """Raised when the uploaded file is not a .pdf or .docx."""


class FileNotFoundErrorService(ResumeServiceError):
    """Raised when the path handed to the parser does not exist on disk."""


class ResumeParseError(ResumeServiceError):
    """Raised when a file is the right type but cannot be read (corrupt, encrypted)."""


class EmptyResumeError(ResumeServiceError):
    """Raised when a file parsed fine but yielded almost no text (e.g. a scan)."""
