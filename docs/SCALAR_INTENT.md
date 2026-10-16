# Scalar preservation and explicit corrections

The local editor supports these complete requests:

- `do not change the floor; only wall thickness to 3mm`
- `keep lid clearance unchanged and walls three mm`
- `only lid clearance 0.4mm`
- `not 4mm walls, make them 3mm`
- `not four millimeters wall thickness; set it to three mm`

`only` applies to one named scalar property. Every other enclosure specification field remains equal to its original value. A conflicting later clause produces no candidate. For a lid property, the other lid properties are preserved individually.

A rejected-value clause needs an immediately adjacent replacement for the same scalar. In that pair, `it` or `them` refers to the named scalar. Those pronouns do not resolve from earlier conversation history. A later correction cannot restore the rejected value, including its equivalent in another unit.

Bare self-corrections retain directional intent: `increase walls to four mm, actually three mm` remains an increase relative to the original project. A correction to a smaller or unchanged value asks for clarification. A full explicit correction such as `actually set walls to one point five mm` supplies a replacement instruction with its own verb.

Every proposal still requires review and is tied to the exact baseline revision. Missing values/units, mismatched references, conflicting preservation and unsupported clauses produce no candidate. The published schema remains v1; the local interpreter identifies itself as `local-conversation-v3`.

This does not implement general Boolean negation, arbitrary fragmented requests, dialogue history or physical validation. See the [development report](../research/development/scalar_intent_20261015/REPORT.md) for measured scope and remaining gates.
