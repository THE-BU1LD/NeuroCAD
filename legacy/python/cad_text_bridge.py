# ============================================================
# TEXT → GRAPH BRIDGE V2
# ============================================================

class TextToGraph:

    def __init__(self, kernel):
        self.kernel = kernel

    def parse(self, text):

        graph = self.kernel.new_graph()

        if "platform" in text:
            graph.add(
                self.kernel.primitive("box", size=[0.8, 0.6, 0.15])
            )

        if "dome" in text:
            graph.smooth_add(
                self.kernel.primitive("sphere", r=0.5),
                k=0.3
            )

        if "torus" in text:
            graph.subtract(
                self.kernel.primitive("torus", R=0.45, r=0.1)
            )

        if "holes" in text:
            for r in [0.0, 0.5]:
                graph.subtract(
                    self.kernel.primitive("cylinder", r=0.07, h=2.0)
                )

        return graph