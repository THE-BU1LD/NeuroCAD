# exceptions.py

class CADException(Exception):
    """Base class for all CAD-related exceptions."""


class IntentParsingError(CADException):
    """Raised when a design request cannot be parsed safely."""


class GeometryError(CADException):
    """Raised when geometric construction fails."""


class TopologyError(CADException):
    """Raised when generated topology violates its contract."""


class KernelFailure(CADException):
    """Raised when the external or internal geometry kernel fails."""


class OptimizationFailure(CADException):
    """Raised when an optimization cannot produce a valid result."""
