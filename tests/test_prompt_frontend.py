from core.prompt_frontend import generate_design
from core.validation import validate_design
from text_to_cad import TextToCAD

THREE_MODIFIER_PROMPT = (
    "a 120 x 80 x 4 mm rounded plate with four 4 mm diameter holes "
    "and one 20 x 8 mm slot and corner radius 5 mm"
)


def test_three_modifier_plate_is_fully_consumed_and_valid() -> None:
    design = generate_design(THREE_MODIFIER_PROMPT)
    report = validate_design(design)

    assert design.metadata["prompt_fully_consumed"] is True
    assert design.metadata["prompt_contract_extension"] == "plate-three-modifier-v1"
    assert design.metadata["hole_count_requested"] == 4
    assert design.metadata["slot_count_requested"] == 1
    assert design.metadata["corner_radius_mm"] == 5.0
    assert report.valid, report.errors


def test_three_modifier_plate_reaches_canonical_ir_and_scad() -> None:
    document = TextToCAD().build(THREE_MODIFIER_PROMPT)

    assert document.validation.valid, document.validation.errors
    assert document.program is not None
    assert document.ir_validation is not None
    assert document.ir_validation.valid, document.ir_validation.errors
    assert document.scad.strip()


def test_wall_thickness_after_label_is_supported_without_defaults() -> None:
    prompt = "a 100 x 60 x 30 mm enclosure with wall thickness 2 mm"
    design = generate_design(prompt)
    report = validate_design(design)

    assert design.metadata["prompt_fully_consumed"] is True
    assert design.metadata["prompt_contract_extension"] == "enclosure-wall-label-v1"
    assert design.metadata["wall_thickness_explicit"] is True
    assert design.metadata["wall_thickness_mm"] == 2.0
    assert report.valid, report.errors


def test_extension_never_consumes_unrecognized_trailing_prose() -> None:
    prompt = THREE_MODIFIER_PROMPT + " and make it magical"
    design = generate_design(prompt)
    report = validate_design(design)

    assert design.metadata["prompt_fully_consumed"] is False
    assert "prompt_contract_extension" not in design.metadata
    assert not report.valid
    assert any("unconsumed or unsupported text" in error for error in report.errors)


def test_existing_base_contract_remains_unchanged() -> None:
    prompt = "a 120 x 80 x 4 mm plate with four 4 mm holes"
    design = generate_design(prompt)
    report = validate_design(design)

    assert design.metadata["prompt_fully_consumed"] is True
    assert "prompt_contract_extension" not in design.metadata
    assert report.valid, report.errors
