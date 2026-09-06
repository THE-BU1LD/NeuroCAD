from text_to_cad import TextToCAD


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate OpenSCAD from a text prompt")
    parser.add_argument("prompt", nargs="+", help="Prompt describing the object")
    parser.add_argument("-o", "--output", default="generated.scad")
    parser.add_argument("--fn", type=int, default=96)
    args = parser.parse_args()

    prompt = " ".join(args.prompt)
    generator = TextToCAD(output_path=args.output, fn=args.fn)
    try:
        path = generator.export(prompt)
    except ValueError as exc:
        parser.error(str(exc))
    print(path)


if __name__ == "__main__":
    main()
