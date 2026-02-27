def generate_report(obj, diagnostics):
    lines = []
    lines.append("DESIGN ANALYSIS REPORT")
    lines.append("-" * 30)

    for d in diagnostics:
        lines.append(d)

    if hasattr(obj, "material"):
        lines.append(f"Material: {obj.material.name}")

        from evaluation import evaluate_design
    from report import generate_report

    result = evaluate_design(obj, learned_risk) # type: ignore
    print(generate_report(obj.name, result))


    return "\n".join(lines)
