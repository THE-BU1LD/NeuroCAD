import torch
from torch import nn
import re


# ============================================================
# TEXT PARSER (symbolic + neural ready)
# ============================================================

class TextParser:

    def parse(self, text):
        text = text.lower()

        shape = None
        params = {}

        # ---- shape detection ----
        if "sphere" in text:
            shape = "sphere"
        elif "box" in text or "cube" in text:
            shape = "box"
        elif "cylinder" in text:
            shape = "cylinder"
        elif "torus" in text or "ring" in text:
            shape = "torus"
        elif "frisbee" in text:
            shape = "frisbee"

        # ---- numbers ----
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
        nums = [float(n) for n in nums]

        if shape == "sphere" and nums:
            params["radius"] = nums[0]

        if shape == "cylinder":
            if len(nums) >= 1:
                params["radius"] = nums[0]
            if len(nums) >= 2:
                params["height"] = nums[1]

        if shape == "box":
            if len(nums) == 1:
                params["size"] = [nums[0]]*3
            if len(nums) >= 3:
                params["size"] = nums[:3]

        return shape, params


# ============================================================
# NEURAL PARAM MODEL
# ============================================================

class TextToParamNet(nn.Module):

    def __init__(self, vocab=128, hidden=64, out=4):
        super().__init__()
        self.embed = nn.Embedding(vocab, hidden)
        self.fc = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, out)
        )

    def forward(self, tokens):
        x = self.embed(tokens).mean(1)
        return self.fc(x)


# ============================================================
# TOKENIZER
# ============================================================

class SimpleTokenizer:

    def __init__(self):
        self.vocab = {}
        self.idx = 0

    def encode(self, text):
        tokens = []
        for w in text.lower().split():
            if w not in self.vocab:
                self.vocab[w] = self.idx
                self.idx += 1
            tokens.append(self.vocab[w])
        return torch.tensor(tokens).unsqueeze(0)


# ============================================================
# TEXT → CAD SYSTEM
# ============================================================

class TextToCAD:

    def __init__(self, cad_kernel):
        self.parser = TextParser()
        self.kernel = cad_kernel
        self.tokenizer = SimpleTokenizer()
        self.net = TextToParamNet()

    def build(self, text):

        # symbolic parse
        shape, params = self.parser.parse(text)

        # neural refine
        tokens = self.tokenizer.encode(text)
        pred = self.net(tokens).detach().numpy()[0]

        if shape == "sphere":
            params.setdefault("radius", abs(pred[0]))

        if shape == "cylinder":
            params.setdefault("radius", abs(pred[0]))
            params.setdefault("height", abs(pred[1]))

        if shape == "box":
            params.setdefault("size", [abs(pred[0])]*3)

        mesh = self.kernel.build(shape, params)

        return mesh
