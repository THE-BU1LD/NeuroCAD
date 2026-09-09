from core.prompt_engine import generate_design
from core.validation import validate_design


def test_legacy_pseudo_domains_are_quarantined() -> None:
    for prompt in ("a fast plane", "electric car", "dc motor", "a wooden desk"):
        design = generate_design(prompt)
        assert design.components == []
        assert not validate_design(design).valid
