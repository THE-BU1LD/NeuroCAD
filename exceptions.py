# exceptions.py

class CADException(Exception):
    """Base class for all CAD-related exceptions."""
    pass


class IntentParsingError(CADException):
    pass


class GeometryError(CADException):
    pass


class TopologyError(CADException):
    pass


class KernelFailure(CADException):
    pass


class OptimizationFailure(CADException):
    pass
