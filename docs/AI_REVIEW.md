# AI review brief: Kupakosh drilling-event review queue

You are reviewing machine-extracted drilling "events" from public well reports (Norway, Australia, Netherlands, USA, India). Each item has:
- a `hazard` label;
- an `evidence` sentence, copied verbatim from the report;
- sometimes a depth.

Your job is to decide, **from the evidence sentence alone**, whether the label is correct. The results feed a safety-decision prototype, so be strict and honest.

## Hazard definitions (taxonomy keys)
- `lost_circulation`: drilling fluid lost to the formation. Examples: losses, lost returns, partial or total losses, LCM pumped to cure losses.
- `kick`: influx of formation fluid or gas into the wellbore. Examples: kick, influx, pit gain, well flowing, well shut in for well control, killing the well.
- `stuck_pipe`: drillstring, casing or tools stuck or held. Examples: stuck, differential sticking, pack-off, overpull needing jarring.
- `torque_spike`: abnormally high or erratic torque, or stalling.
- `overpressure`: higher pore pressure than expected. Examples: high gas levels, connection or trip gas, abnormal pressure, mud weight raised for pressure.
- `cementing_issue`: a problem with a cement job. Examples: losses during cementing, poor bond, squeeze or remedial cement, no returns while cementing.
- `fishing`: retrieving junk or a parted or lost string from the hole. Examples: fishing, fish, twist-off, parted pipe, lost in hole.
- `wellbore_instability`: hole problems. Examples: tight hole, cavings, collapse, washouts, reaming or back-reaming because of hole condition, bit balling in reactive clays.

## Decision for each item
- **"confirm"**: the sentence states that this hazard actually happened during drilling, completion, testing or workover of this well.
- **"relabel"**: a drilling problem really happened, but the correct key is a different one from the list. Give `hazard`.
- **"reject"**: any of these:
  - negated ("no losses were experienced", "no problems");
  - hypothetical, planned or a recommendation ("to avoid losses", "risk of", "prepared for");
  - generic text or a procedure, not an occurrence;
  - a different topic, such as a production or reservoir "loss", or "pressure" as a measurement only;
  - an equipment or rig problem that is not downhole;
  - weather (WOW);
  - too garbled to tell (OCR noise).

"Hole problems and WOW delayed the well" counts as a real occurrence of `wellbore_instability`, so confirm it.

When one sentence reports two hazards, it appears as two items; judge each label separately. For example, "the pipe stuck and parted" is both `stuck_pipe` (confirm) and `fishing`. Fishing is confirmed only if the sentence mentions retrieval, a fish or lost equipment. Parting pipe alone implies a fish, so confirm fishing for "parted".

## Depth (optional, strict)
Add a depth only when the sentence explicitly gives the depth at which **this** problem occurred:
- `depth_quote`: the exact verbatim substring from the evidence, for example "3150 m" or "at 10,340 ft".
- `depth_value`: the number, for example 3150.
- `depth_unit`: "m" or "ft".

Never infer, estimate or compute a depth. Never use a casing size, a mud weight, or a depth that belongs to something else. If in doubt, leave the depth out.

## Output
Write a JSON array to the output path you are given, one object per input item, in the same order:
```json
{"id": 123, "decision": "confirm|relabel|reject", "hazard": "only for relabel", "depth_quote": "...", "depth_value": 0, "depth_unit": "m", "reason": "<= 15 words"}
```
Omit the depth fields when there is no depth. Cover every id exactly once. Do not skip items and do not invent ids.

Work through the whole file carefully, in batches. Use Python to load the input, and write the output with Python `json.dump`. Finally, validate that the count of your decisions equals the count of input items and that every id matches. Do not modify any project files.
