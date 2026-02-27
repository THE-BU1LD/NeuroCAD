from core.prompt_engine import generate_design

def test_plane():
    d = generate_design("a fast plane")
    assert len(d.components) >= 2

def test_car():
    d = generate_design("electric car")
    assert len(d.components) >= 2

def test_motor():
    d = generate_design("dc motor")
    assert len(d.components) >= 2
