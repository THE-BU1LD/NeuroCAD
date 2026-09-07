# NeuroCAD demo and trial outreach playbook

No message in this file has been sent. The product is an alpha with no public
release yet, so outreach must remain in draft until a sender authorizes the
channel and an anonymously installable candidate exists.

## Target customer profile

Prioritize engineers and tool builders who repeatedly create small, explicitly
dimensioned plates or electronics enclosures and can evaluate SCAD/STL exchange.
The best early evaluator has a real reference part, can inspect geometry, and is
willing to report a failed prompt. Avoid safety-critical, production-certified,
arbitrary surfacing, assembly, or native-BREP expectations.

## Qualified routes and tailored drafts

### CAD automation — Onshape developer relations

Why relevant: Onshape publicly supports partner/API integrations and provides a
developer-relations route. NeuroCAD does **not** yet have an Onshape API
integration, so the ask is workflow discovery, not a partnership claim.

Route: <https://www.onshape.com/en/app-integrations/faq>

Subject: Feedback request: bounded prompt-to-SCAD/STL enclosure compiler

> I am testing NeuroCAD, an alpha deterministic compiler for explicitly
> dimensioned plates, primitives, and electronics enclosures. It emits validated
> JSON and editable OpenSCAD, and can kernel-verify STL; it does not create native
> Onshape documents today. Would someone on the developer-relations team be open
> to a 20-minute workflow review focused on what a credible Onshape handoff would
> require? I can share a five-minute reproducible demo and would value a blunt
> “not useful” result as much as a positive one. No mailing list follow-up unless
> requested.

### Electronics enclosures — Protocase product/design team

Why relevant: Protocase offers enclosure design software and services for users
who may not be CAD specialists. Ask for a boundary review; never imply that
NeuroCAD output is production-ready or compatible with their ordering system.

Route: <https://www.protocase.com/contact/>

Subject: Can your enclosure team break this narrow prompt-to-STL prototype?

> I am looking for expert negative feedback on NeuroCAD, an alpha tool that turns
> fully dimensioned electronics-enclosure clauses into editable SCAD and verified
> body/lid STL. It currently handles a bounded set of walls, lids, cutouts, vents,
> PCB envelopes, and standoffs; it does not perform sheet-metal DFM, quoting, or
> physical validation. Could a designer spare 20 minutes to try one non-sensitive
> reference enclosure and identify the first unacceptable assumption? I will not
> describe your participation as endorsement, and I will not follow up after a
> decline.

### Maker tooling — Adafruit community

Why relevant: Adafruit directs technical discussion to its community forums and
Show and Tell rather than one-to-one engineering email. Use the community route
only after reading its posting rules; do not send a sales request to support.

Route: <https://www.adafruit.com/support>

Post title: Alpha test: strict dimensioned prompt to editable enclosure + STL

> I built a small open-source-style alpha that accepts only explicitly
> dimensioned plates, primitives, and enclosure clauses, then emits JSON, SCAD,
> and OpenSCAD-verified STL. It deliberately rejects general or incomplete
> prompts. If this is appropriate for this forum, I would appreciate one real
> maker enclosure prompt and the generated-artifact receipt needed to reproduce
> any failure. This is not a safety or manufacturability tool, and I will remove
> the post if it is off-topic.

### 3D printing — Prusa Research / Printables workflow team

Why relevant: Prusa publishes STL-oriented maker workflows and official brand
models. NeuroCAD does not slice, select a printer profile, or produce G-code;
the evaluation target is artifact handoff and failure reporting.

Route: <https://www.prusa3d.com/en/page/ask-us-anything_482/>

Subject: Trial request: verified enclosure STL handoff, before slicing

> I am testing NeuroCAD, an alpha prompt-to-OpenSCAD tool for small, fully
> dimensioned parts and electronics enclosures. It verifies mesh topology and
> requested dimensions before handoff but does not slice, generate G-code, or
> claim printability. Is there an appropriate product/community contact who could
> try the five-minute artifact kit and tell me whether its receipt and failure
> messages are useful before a model enters a slicer? I am asking for product
> feedback only, not endorsement or promotion.

### EDA-adjacent — Flux product team

Why relevant: Flux positions itself around AI-assisted PCB workflows and offers
an official sales/contact route. NeuroCAD's current board path is a bounded,
source-hash-bound KiCad extractor—not a Flux integration—so ask which mechanical
facts an EDA-to-enclosure handoff should preserve.

Route: <https://www.flux.ai/p/contact-sales>

Subject: Workflow feedback: explicit PCB facts into a verified enclosure

> I am evaluating NeuroCAD, an alpha deterministic enclosure compiler with a
> narrow, hash-bound KiCad board-envelope path. It never guesses connector
> cutouts or mounting decisions and has no Flux integration today. Would a
> product or applications engineer be willing to review a 20-minute demo and say
> which source-bound mechanical facts would make an EDA-to-enclosure handoff
> credible? I can provide exact artifacts and welcome a negative result. This is
> a one-time request; no further contact unless invited.

## Send gate

Before sending any single message, record: named sender and organization,
authorized account/channel, recipient role and relevance, final reviewed copy,
public release URL, artifact receipt, local-law/recipient-policy check, and a
clear one-time/opt-out statement. Do not scrape personal emails or send a bulk
sequence.

## Outcome ledger

| Organization | Route | Sent UTC | Replied UTC | Demo booked | Trial started | Failure captured | Product feedback | Owner | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Onshape | Developer relations | not sent | — | no | no | no | none | unassigned | Release URL and sender authorization missing |
| Protocase | Contact form | not sent | — | no | no | no | none | unassigned | Release URL and sender authorization missing |
| Adafruit | Community route | not posted | — | no | no | no | none | unassigned | Must confirm forum appropriateness first |
| Prusa Research | Public contact route | not sent | — | no | no | no | none | unassigned | Release URL and sender authorization missing |
| Flux | Contact sales | not sent | — | no | no | no | none | unassigned | Release URL and sender authorization missing |
