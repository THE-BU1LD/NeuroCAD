# Controlled compiler data card

**Name:** NeuroCAD Controlled Compiler Stress v1  
**Generator:** `core.research_suite:generate_compiler_stress_tasks`  
**Seed:** 20260902  
**Rows:** 240  
**Unit of analysis:** one prompt and exact semantic signature  
**Splits:** deterministic 60/20/20 labels  
**Intended use:** regression, controlled unit/lexical/composition evaluation  
**Out of scope:** training a language model, natural-language coverage, safety or manufacturability claims

Each row has `task_id`, `split`, `family`, `prompt`, and `expected`. The generator rejects exact duplicate prompts. Expected values are produced from sampled source parameters before prompt compilation. The run manifest hashes the serialized JSONL. Known bias: templates are authored to the compiler contract, English only, short, and dimension-centric.

