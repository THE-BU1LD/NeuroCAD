# NVIDIA DSX Integration Plan for NeuroCAD

## Goal

Use NVIDIA DSX concepts where they materially improve NeuroCAD today, without pretending a laptop development environment is an AI factory.

## What maps cleanly

### 1. NIM / hosted inference
NeuroCAD can use NVIDIA's OpenAI-compatible hosted API as an advisory model layer for diagnosis, repair proposals, experiment review, and multimodal/CAD reasoning. Deterministic parser and geometry validation remain authoritative.

### 2. DSX Agent Gateway pattern
DSX Agent Gateway is an MCP ingress pattern with authentication, tenant authorization, rate limiting, upstream routing, and observability. NeuroCAD/Percy should eventually expose tools through a single gateway rather than giving agents unrestricted machine access.

Recommended logical targets:
- neurocad-parser
- neurocad-verifier
- neurocad-test-runner
- neurocad-experiment-ledger
- neurocad-artifact-inspector

### 3. DSX Exchange pattern
Use an event bus when Percy/NeuroCAD becomes multi-worker. Suggested event vocabulary:
- task.created
- task.claimed
- test.completed
- verification.completed
- experiment.completed
- artifact.created
- worker.failed
- review.completed

Each event should contain task_id, run_id, producer, timestamp, schema_version, evidence references, and status.

### 4. Dynamo / scalable inference
Do not deploy Dynamo locally just to say NeuroCAD uses DSX. Adopt the interface boundary now so a self-hosted multi-GPU inference service can replace hosted NIM later without rewriting the research pipeline.

### 5. Observability
Every agent/model call should record:
- run_id
- task type
- model
- request latency
- token usage
- HTTP/result status
- verifier status before repair
- verifier status after repair
- number of repair iterations
- associated git SHA

## Immediate architecture

```text
User / Percy
    |
    v
Task Router
    |
    +--> deterministic NeuroCAD tools
    |      +--> parser
    |      +--> geometry verifier
    |      +--> tests
    |      +--> evidence ledger
    |
    +--> NVIDIA model review layer
           +--> diagnosis
           +--> proposed repair
           +--> research critic

All claims -> deterministic verification -> evidence ledger
```

## Non-goals

- Do not weaken parser/verifier gates to accommodate model output.
- Do not treat LLM reasoning as experimental evidence.
- Do not deploy Kubernetes/Run:ai/KAI Scheduler on a MacBook merely for architectural similarity.
- Do not add distributed inference infrastructure before workload volume requires it.
- Do not place NVIDIA API keys in git history.

## Phase 1 — now

- [x] Hosted NVIDIA API connectivity established.
- [x] Add deterministic-evidence-first NVIDIA audit script.
- [ ] Run the audit against current main and save the output.
- [ ] Classify failing tests by first causal break.
- [ ] Add model/latency/token metrics for every NVIDIA request.
- [ ] Add a provider interface so NeuroCAD is not coupled to one model endpoint.

## Phase 2 — Percy integration

- [ ] Create a provider router with `nvidia`, `openai`, and `local` backends.
- [ ] Add capability routing: fast, reasoning, code, vision.
- [ ] Create an event schema shared by Percy and NeuroCAD workers.
- [ ] Make repair agents consume immutable test/verifier artifacts.
- [ ] Require deterministic re-verification before a task can close.

## Phase 3 — gateway and observability

- [ ] Expose safe tools through MCP.
- [ ] Put a gateway in front of MCP tools.
- [ ] Add auth, per-tenant permissions, rate limits, structured logs, traces, and metrics.
- [ ] Keep shell execution isolated from model processes.

## Phase 4 — GPU scale only when justified

When workloads justify dedicated NVIDIA hardware or cloud GPU clusters:
- Evaluate Dynamo for distributed inference serving.
- Evaluate Kubernetes GPU Operator for cluster runtime management.
- Evaluate Run:ai/KAI Scheduler only when there is shared multi-user GPU capacity.
- Add cluster health/burn-in tooling before trusting long experiments.

## First command

```bash
export NVIDIA_API_KEY='...'
brew install jq  # only if jq is missing
chmod +x scripts/nvidia_dsx_audit.sh
./scripts/nvidia_dsx_audit.sh
```

Review artifacts appear under `.neurocad-audit/nvidia-dsx/` and must not be treated as verified findings until the deterministic evidence supports them.
