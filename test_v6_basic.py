from cad_master_kernel import UniversalCADCoreV6

core = UniversalCADCoreV6()

tests = [
    "frisbee 27cm",
    "katana 1m",
    "bowl 20cm",
    "dome 30cm"
]

for t in tests:
    print("\n=== TEST:", t, "===")
    result = core.generate(
        t,
        bounds=1.5,
        res=64
    )
    print(result)
