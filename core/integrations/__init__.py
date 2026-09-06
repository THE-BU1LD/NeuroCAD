"""Honest, file-first application interoperability for typed NeuroCAD builds."""

from .common import safe_filename_stem
from .exchange import (
    EXCHANGE_VERSION,
    ExchangeBundle,
    create_neutral_manifest,
    export_openscad_bundle,
    write_neutral_manifest,
)
from .handoff import (
    HANDOFF_VERSION,
    VERIFICATION_VERSION,
    create_application_handoff,
    verify_exchange_bundle,
    write_application_handoff,
)
from .kicad import (
    KICAD_EXTRACTION_DRAFT_VERSION,
    KICAD_FILE_EXTRACTOR_VERSION,
    KICAD_HANDOFF_VERSION,
    KICAD_MECHANICAL_REVIEW_VERSION,
    KiCadBoard,
    KiCadConnector,
    KiCadHandoffError,
    KiCadMountingHole,
    KiCadProjectApplication,
    apply_kicad_board_to_project,
    bind_kicad_extraction,
    create_kicad_extraction_request,
    parse_kicad_handoff,
    read_kicad_handoff,
    write_bound_kicad_extraction,
    write_kicad_extraction_request,
)
from .kicad_file import extract_kicad_file_receipt, write_kicad_file_receipt
from .model import (
    ApplicationAdapter,
    Capability,
    CapabilityState,
    IntegrationUnavailableError,
    Prerequisite,
)
from .registry import AdapterRegistry, default_registry

__all__ = [
    "EXCHANGE_VERSION",
    "HANDOFF_VERSION",
    "KICAD_EXTRACTION_DRAFT_VERSION",
    "KICAD_FILE_EXTRACTOR_VERSION",
    "KICAD_HANDOFF_VERSION",
    "KICAD_MECHANICAL_REVIEW_VERSION",
    "VERIFICATION_VERSION",
    "AdapterRegistry",
    "ApplicationAdapter",
    "Capability",
    "CapabilityState",
    "ExchangeBundle",
    "IntegrationUnavailableError",
    "KiCadBoard",
    "KiCadConnector",
    "KiCadHandoffError",
    "KiCadMountingHole",
    "KiCadProjectApplication",
    "Prerequisite",
    "apply_kicad_board_to_project",
    "bind_kicad_extraction",
    "create_application_handoff",
    "create_kicad_extraction_request",
    "create_neutral_manifest",
    "default_registry",
    "export_openscad_bundle",
    "extract_kicad_file_receipt",
    "parse_kicad_handoff",
    "read_kicad_handoff",
    "safe_filename_stem",
    "verify_exchange_bundle",
    "write_application_handoff",
    "write_bound_kicad_extraction",
    "write_kicad_extraction_request",
    "write_kicad_file_receipt",
    "write_neutral_manifest",
]
