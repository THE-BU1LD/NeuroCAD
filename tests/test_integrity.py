from core.prompt_engine import generate_design

if __name__ == "__main__":
    design = generate_design("simple aircraft wing")

    print("Components:")
    for c in design.components:
        print("-", c.name)

    print("\nConnections:")
    for a, b in design.connections:
        print(a.name, "↔", b.name)
