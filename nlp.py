import re
from parts import Part


def parse_mass(text):
    m = re.search(r"mass\s*(\d+)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\s*kg", text)
    if m:
        return float(m.group(1))
    return 50.0


def parse_position(text):
    m = re.search(r"\((-?\d+\.?\d*),\s*(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)", text)
    if m:
        return (
            float(m.group(1)),
            float(m.group(2)),
            float(m.group(3)),
        )
    return (0.0, 0.0, 0.0)


def detect_name(text):
    s = text.lower()

    if "wing" in s:
        return "Wing"

    if "fuselage" in s:
        return "Fuselage"

    if "engine" in s:
        return "Engine"

    if "tail" in s:
        return "Tail"

    if "propeller" in s:
        return "Propeller"

    if "body" in s:
        return "Body"

    return None


def extract_parts(prompt):

    parts = []

    sentences = re.split(r"[.;\n]", prompt)

    for s in sentences:

        name = detect_name(s)

        if name is None:
            continue

        mass = parse_mass(s)

        position = parse_position(s)

        parts.append(Part(name, mass, position))

    return parts


def prompt_to_parts(prompt):

    parts = extract_parts(prompt)

    if len(parts) == 0:
        raise ValueError("No parts detected")

    return parts

    import re
import math
from parts import Part


def parse_mass(text):
    m = re.search(r"mass\s*(\d+)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\s*kg", text)
    if m:
        return float(m.group(1))
    return 50.0


def parse_position(text):
    m = re.search(r"\((-?\d+\.?\d*),\s*(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)", text)
    if m:
        return (
            float(m.group(1)),
            float(m.group(2)),
            float(m.group(3)),
        )
    return None


def parse_count(text):
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    words = {
        "one":1,"two":2,"three":3,"four":4,"five":5,"six":6,
        "seven":7,"eight":8,"nine":9
    }
    for w in words:
        if w in text.lower():
            return words[w]
    return 1


def detect_name(text):
    s = text.lower()

    if "wing" in s:
        return "Wing"

    if "fuselage" in s:
        return "Fuselage"

    if "engine" in s:
        return "Engine"

    if "tail" in s:
        return "Tail"

    if "propeller" in s:
        return "Propeller"

    if "panel" in s:
        return "Panel"

    if "body" in s:
        return "Body"

    return None


def generate_symmetric_positions(n, radius=1.0, z=0.0):

    pos = []

    for i in range(n):
        a = (2*math.pi*i)/n
        x = radius*math.cos(a)
        y = radius*math.sin(a)
        pos.append((round(x,3),round(y,3),z))

    return pos


def extract_parts(prompt):

    parts = []

    sentences = re.split(r"[.;\n]", prompt)

    for s in sentences:

        name = detect_name(s)

        if name is None:
            continue

        mass = parse_mass(s)

        pos = parse_position(s)

        count = parse_count(s)

        if pos is not None:
            parts.append(Part(name,mass,pos))
            continue

        if count > 1:
            positions = generate_symmetric_positions(count)

            for p in positions:
                parts.append(Part(name,mass,p))
        else:
            parts.append(Part(name,mass,(0.0,0.0,0.0)))

    return parts


def prompt_to_parts(prompt):

    parts = extract_parts(prompt)

    if len(parts) == 0:
        raise ValueError("No parts detected")

    return parts


def generate_parts_block(parts):

    lines = []
    lines.append("parts = [")

    for p in parts:
        line = f'    Part("{p.name}", {p.mass}, {p.position}),'
        lines.append(line)

    lines.append("]")
    return "\n".join(lines)


def generate_script(parts):

    block = generate_parts_block(parts)

    script = f'''
from parts import Part
from auto_joint import auto_generate_joints
from system_optimizer import SystemOptimizer
from stress_test import monte_carlo_test, adversarial_test
from ml import TinyNeuralScorer

{block}

joints = auto_generate_joints(parts)

loads = {{j:120.0 for j in joints}}

sys_opt = SystemOptimizer(joints, loads)
summary = sys_opt.optimize()

print("\\n[OPTIMIZED JOINTS]")
for s in summary:
    print(s)

print("\\n[MONTE CARLO FAILURES]")
print(len(monte_carlo_test(joints, loads)))

print("\\n[ADVERSARIAL TEST]")
for j, r in adversarial_test(joints):
    print(j.describe(), "risk=", round(r,3))

model = TinyNeuralScorer()

print("\\n[ML SCORES]")
for j in joints:
    print(j.describe(), model.score(j, loads[j]))
'''
    return script


def prompt_to_script(prompt):

    parts = prompt_to_parts(prompt)

    return generate_script(parts)


def write_script(prompt, filename="generated_design.py"):

    script = prompt_to_script(prompt)

    with open(filename,"w") as f:
        f.write(script)

    return filename
import re
import math
from parts import Part


def parse_mass(text):
    m = re.search(r"mass\s*(\d+)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\s*kg", text)
    if m:
        return float(m.group(1))
    return 50.0


def parse_position(text):
    m = re.search(r"\((-?\d+\.?\d*),\s*(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)", text)
    if m:
        return (
            float(m.group(1)),
            float(m.group(2)),
            float(m.group(3)),
        )
    return None


def parse_count(text):
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    words = {
        "one":1,"two":2,"three":3,"four":4,"five":5,"six":6,
        "seven":7,"eight":8,"nine":9
    }
    for w in words:
        if w in text.lower():
            return words[w]
    return 1


def detect_name(text):
    s = text.lower()

    if "wing" in s:
        return "Wing"

    if "fuselage" in s:
        return "Fuselage"

    if "engine" in s:
        return "Engine"

    if "tail" in s:
        return "Tail"

    if "propeller" in s:
        return "Propeller"

    if "panel" in s:
        return "Panel"

    if "fin" in s:
        return "Fin"

    if "body" in s:
        return "Body"

    return None


def symmetric_circle(n, r=1.0, z=0.0):
    pos = []
    for i in range(n):
        a = (2*math.pi*i)/n
        x = r*math.cos(a)
        y = r*math.sin(a)
        pos.append((round(x,3),round(y,3),z))
    return pos


def rocket_fin_layout(n):
    pos = []
    for i in range(n):
        a = (2*math.pi*i)/n
        x = 0.5*math.cos(a)
        y = 0.5*math.sin(a)
        pos.append((round(x,3),round(y,3),-1.0))
    return pos


def airplane_wing_layout():
    return [(-1.5,0,0),(1.5,0,0)]


def satellite_panel_layout(n):
    pos = []
    for i in range(n):
        x = (-1)**i * 2.0
        y = i * 0.2
        pos.append((x,y,0))
    return pos


def generate_layout(name, count):

    if name == "Propeller":
        return symmetric_circle(count,1.2,0)

    if name == "Fin":
        return rocket_fin_layout(count)

    if name == "Wing" and count == 2:
        return airplane_wing_layout()

    if name == "Panel":
        return satellite_panel_layout(count)

    return symmetric_circle(count)


def extract_parts(prompt):

    parts = []

    sentences = re.split(r"[.;\n]", prompt)

    for s in sentences:

        name = detect_name(s)

        if name is None:
            continue

        mass = parse_mass(s)

        pos = parse_position(s)

        count = parse_count(s)

        if pos is not None:
            parts.append(Part(name,mass,pos))
            continue

        if count > 1:
            layout = generate_layout(name,count)

            for p in layout:
                parts.append(Part(name,mass,p))
        else:
            parts.append(Part(name,mass,(0.0,0.0,0.0)))

    return parts


def prompt_to_parts(prompt):

    parts = extract_parts(prompt)

    if len(parts) == 0:
        raise ValueError("No parts detected")

    return parts


def generate_parts_block(parts):

    lines = []
    lines.append("parts = [")

    for p in parts:
        line = f'    Part("{p.name}", {p.mass}, {p.position}),'
        lines.append(line)

    lines.append("]")
    return "\n".join(lines)


def generate_script(parts):

    block = generate_parts_block(parts)

    script = f'''
from parts import Part
from auto_joint import auto_generate_joints
from system_optimizer import SystemOptimizer
from stress_test import monte_carlo_test, adversarial_test
from ml import TinyNeuralScorer

{block}

joints = auto_generate_joints(parts)

loads = {{j:120.0 for j in joints}}

sys_opt = SystemOptimizer(joints, loads)
summary = sys_opt.optimize()

print("\\n[OPTIMIZED JOINTS]")
for s in summary:
    print(s)

print("\\n[MONTE CARLO FAILURES]")
print(len(monte_carlo_test(joints, loads)))

print("\\n[ADVERSARIAL TEST]")
for j, r in adversarial_test(joints):
    print(j.describe(), "risk=", round(r,3))

model = TinyNeuralScorer()

print("\\n[ML SCORES]")
for j in joints:
    print(j.describe(), model.score(j, loads[j]))
'''
    return script


def prompt_to_script(prompt):

    parts = prompt_to_parts(prompt)

    return generate_script(parts)


def write_script(prompt, filename="generated_design.py"):

    script = prompt_to_script(prompt)

    with open(filename,"w") as f:
        f.write(script)

    return filename

import re
import math
from parts import Part


def parse_mass(text):
    m = re.search(r"mass\s*(\d+)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\s*kg", text)
    if m:
        return float(m.group(1))
    return 50.0


def parse_position(text):
    m = re.search(r"\((-?\d+\.?\d*),\s*(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)", text)
    if m:
        return (
            float(m.group(1)),
            float(m.group(2)),
            float(m.group(3)),
        )
    return None


def parse_count(text):
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    words = {
        "one":1,"two":2,"three":3,"four":4,"five":5,"six":6,
        "seven":7,"eight":8,"nine":9
    }
    for w in words:
        if w in text.lower():
            return words[w]
    return 1


def detect_name(text):
    s = text.lower()

    if "wing" in s:
        return "Wing"

    if "fuselage" in s:
        return "Fuselage"

    if "engine" in s:
        return "Engine"

    if "tail" in s:
        return "Tail"

    if "propeller" in s:
        return "Propeller"

    if "panel" in s:
        return "Panel"

    if "fin" in s:
        return "Fin"

    if "body" in s:
        return "Body"

    return None


def symmetric_circle(n, r=1.0, z=0.0):
    pos = []
    for i in range(n):
        a = (2*math.pi*i)/n
        x = r*math.cos(a)
        y = r*math.sin(a)
        pos.append((round(x,3),round(y,3),z))
    return pos


def rocket_fin_layout(n):
    pos = []
    for i in range(n):
        a = (2*math.pi*i)/n
        x = 0.5*math.cos(a)
        y = 0.5*math.sin(a)
        pos.append((round(x,3),round(y,3),-1.0))
    return pos


def airplane_wing_layout():
    return [(-1.5,0,0),(1.5,0,0)]


def satellite_panel_layout(n):
    pos = []
    for i in range(n):
        x = (-1)**i * 2.0
        y = i * 0.2
        pos.append((x,y,0))
    return pos


def generate_layout(name, count):

    if name == "Propeller":
        return symmetric_circle(count,1.2,0)

    if name == "Fin":
        return rocket_fin_layout(count)

    if name == "Wing" and count == 2:
        return airplane_wing_layout()

    if name == "Panel":
        return satellite_panel_layout(count)

    return symmetric_circle(count)


def detect_vehicle_type(prompt):

    p = prompt.lower()

    if "rocket" in p:
        return "rocket"

    if "satellite" in p:
        return "satellite"

    if "drone" in p:
        return "drone"

    if "airplane" in p or "aircraft" in p:
        return "airplane"

    return "generic"


def enforce_design_grammar(vehicle, parts):

    names = [p.name for p in parts]

    if vehicle == "airplane":
        if "Fuselage" not in names:
            parts.append(Part("Fuselage",120,(0,0,0)))
        if names.count("Wing") < 2:
            w = airplane_wing_layout()
            parts.append(Part("Wing",60,w[0]))
            parts.append(Part("Wing",60,w[1]))

    if vehicle == "rocket":
        if "Body" not in names:
            parts.append(Part("Body",150,(0,0,0)))
        if "Fin" not in names:
            for p in rocket_fin_layout(3):
                parts.append(Part("Fin",20,p))

    if vehicle == "drone":
        if "Body" not in names:
            parts.append(Part("Body",40,(0,0,0)))
        if names.count("Propeller") < 4:
            for p in symmetric_circle(4,1.2,0):
                parts.append(Part("Propeller",15,p))

    if vehicle == "satellite":
        if "Body" not in names:
            parts.append(Part("Body",70,(0,0,0)))
        if "Panel" not in names:
            for p in satellite_panel_layout(4):
                parts.append(Part("Panel",10,p))

    return parts


def infer_load(prompt):

    m = re.search(r"load\s*(\d+)", prompt.lower())
    if m:
        return float(m.group(1))

    if "rocket" in prompt.lower():
        return 300.0

    if "airplane" in prompt.lower():
        return 200.0

    if "drone" in prompt.lower():
        return 80.0

    if "satellite" in prompt.lower():
        return 40.0

    return 120.0


def validate_parts(parts):

    cleaned = []

    seen = set()

    for p in parts:
        key = (p.name,p.position)
        if key not in seen:
            cleaned.append(p)
            seen.add(key)

    return cleaned


def extract_parts(prompt):

    parts = []

    sentences = re.split(r"[.;\n]", prompt)

    for s in sentences:

        name = detect_name(s)

        if name is None:
            continue

        mass = parse_mass(s)

        pos = parse_position(s)

        count = parse_count(s)

        if pos is not None:
            parts.append(Part(name,mass,pos))
            continue

        if count > 1:
            layout = generate_layout(name,count)

            for p in layout:
                parts.append(Part(name,mass,p))
        else:
            parts.append(Part(name,mass,(0.0,0.0,0.0)))

    return parts


def prompt_to_parts(prompt):

    parts = extract_parts(prompt)

    vehicle = detect_vehicle_type(prompt)

    parts = enforce_design_grammar(vehicle, parts)

    parts = validate_parts(parts)

    if len(parts) == 0:
        raise ValueError("No parts detected")

    return parts


def generate_parts_block(parts):

    lines = []
    lines.append("parts = [")

    for p in parts:
        line = f'    Part("{p.name}", {p.mass}, {p.position}),'
        lines.append(line)

    lines.append("]")
    return "\n".join(lines)


def generate_script(parts, load):

    block = generate_parts_block(parts)

    script = f'''
from parts import Part
from auto_joint import auto_generate_joints
from system_optimizer import SystemOptimizer
from stress_test import monte_carlo_test, adversarial_test
from ml import TinyNeuralScorer

{block}

joints = auto_generate_joints(parts)

loads = {{j:{load} for j in joints}}

sys_opt = SystemOptimizer(joints, loads)
summary = sys_opt.optimize()

print("\\n[OPTIMIZED JOINTS]")
for s in summary:
    print(s)

print("\\n[MONTE CARLO FAILURES]")
print(len(monte_carlo_test(joints, loads)))

print("\\n[ADVERSARIAL TEST]")
for j, r in adversarial_test(joints):
    print(j.describe(), "risk=", round(r,3))

model = TinyNeuralScorer()

print("\\n[ML SCORES]")
for j in joints:
    print(j.describe(), model.score(j, loads[j]))
'''
    return script


def prompt_to_script(prompt):

    parts = prompt_to_parts(prompt)

    load = infer_load(prompt)

    return generate_script(parts, load)


def write_script(prompt, filename="generated_design.py"):

    script = prompt_to_script(prompt)

    with open(filename,"w") as f:
        f.write(script)

    return filename