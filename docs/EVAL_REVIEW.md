# Eval gold files — second labelling pass

**Second pass by an AI model; not human-verified.** This is an independent second
labelling pass done by an AI assistant, run separately from whatever
process produced `data/eval/events_gold.csv`, `episodes_gold.csv`, and
`copilot_questions.csv` (also AI-labelled, per their own `labeller` columns). Its
purpose is only to surface disagreements between two independent AI passes and to
check for reference drift after the database rebuild (E1+E3, commit 6be2ed2) —
it does **not** substitute for a human reviewing the gold files, and none of the
numbers below should be presented as ground truth.

Full row-by-row output: `data/eval/review/events_second_pass.csv`,
`data/eval/review/episodes_second_pass.csv`, `data/eval/review/copilot_questions_check.csv`.

## 0. Reference drift after the DB rebuild — none found

All `doc:<id>#<locator>` and `passage_id` references in all three gold files were
checked against the rebuilt `data/kupakosh.db` (215,830 passages, 2,748 documents):

- `events_gold.csv` (50 rows, keyed by `passage_id`): every `passage_id` still
  exists and its stored text matches the gold `text` column exactly. 50/50 OK.
- `episodes_gold.csv` (30 rows, keyed by `doc:<id>#<locator>`): every ref resolves
  to a passage whose text matches `event_text` exactly. 30/30 OK.
- `copilot_questions.csv` (25 answerable rows, keyed the same way): every
  `expected_source` resolves to an existing passage. 25/25 OK.

**Conclusion: no gold refs are broken by the rebuild.** `backend/app/eval/run.py`
is scoring the passages it was meant to score. This was the most important thing
to check and it came back clean.

## 1. events_gold.csv — hazard labelling

Agreement: **48/50 (96%)** on the hazard set. No depth disagreements (all rows with
a `true_md_m` value matched the depth mentioned in the sentence).

Two disagreements, both the same underlying issue — a geological/reservoir
pressure *comparison* (between formations, from logs/RFT/cores) mislabelled as an
`overpressure` drilling event, rather than `none`:

| passage_id | text | gold | my label | reason |
|---|---|---|---|---|
| 4017 | "...ca 3 bar overpressured compared to the Hugin Formation." | overpressure | none | Relative reservoir-pressure statement between two formations, not an operational drilling incident (no kick, no gas peak, no mud-weight response). Same category the gold file itself correctly excludes for pid 22275 ("tight formation" = reservoir quality, not a hole problem). |
| 36743 | "...the gas was overpressured, and trapped in a non-reservoir lithology." | overpressure | none | Same pattern: a seal/trap description from wireline-log and core study, not an event that happened while drilling. |

This is a labelling-consistency gap rather than a factual error — the taxonomy's
`overpressure` keyword patterns (`config/taxonomy.yaml`) are broad enough to catch
these geological descriptions, and the same judgment that correctly excluded
pid 22275 wasn't applied to 4017/36743. Worth a rule note (or a taxonomy `exclude`
pattern for "compared to the X Formation" / "trapped in") if the team wants the
distinction enforced mechanically rather than left to labeller judgment.

## 2. episodes_gold.csv — outcome labelling

Agreement: **30/30 (100%)**, including the 5 rows correctly marked `n/a` (not a
real problem episode) and the 1 `worsened` row.

Unlike a labelling pass done on `event_text` alone, each row was checked against
the surrounding narrative (the 1-4 sentences before/after the triggering sentence,
same document, same paragraph) since these are well-history/WCR summary
narratives rather than day-by-day DDRs — the true outcome usually isn't in the
single trigger sentence. With that context, all 30 gold outcomes look correct,
including some genuinely subtle ones:
- `doc:1029#p4.s2` (fishing → `partial`): text says "until **most** of it was
  recovered" — not a full recovery, so `partial` rather than the more literal
  `resolved` a keyword match on "recovered" would produce. Gold got this right.
- `doc:749#p4.s3` (kick → `unknown`): the sentences right after are about an
  unrelated stuck-pipe/sidetrack, so the kick's own resolution is genuinely never
  stated in the window. Gold's own note flags this correctly.

No disagreements to report here.

## 3. copilot_questions.csv — question/source sanity check

29/30 reasonable. The 5 refusal questions are all genuinely out of scope for this
corpus (no geomechanics figures are computed, no commodity prices, no Indian/Assam
well data, no corporate-personnel data) — refusal is the right answer for all 5.

One answerable question has a **stale expected_source**, flagged as important:

- **"Was there fishing in well 30/9-21 S?" → `doc:852#p4.4`.** The passage text is
  *"...operations were suspended for a day because a trawler's fishing net had
  become snagged around anchor chain #7."* — a real marine fishing-net incident,
  not the drilling "fishing" hazard (retrieving lost/broken tools). No event with
  `hazard='fishing'` exists for this well in the current database (checked
  directly). `copilot_questions.csv` is generated deterministically by
  `app/eval/run.py:make_copilot_questions` from whatever events the extraction
  pipeline produced *at generation time*; the fishing-vs-fishing-net false
  positive was since fixed (commit 9c883ca, "fishing-community text is not
  fishing" — matches the taxonomy's own `fishing.exclude` pattern for
  `fishing net`), but the questions CSV was never regenerated after that fix. If
  the copilot eval is run now, this question will likely score as a citation miss
  even though refusing/finding-nothing is the *correct* behaviour post-fix — the
  eval would be penalizing a fix. **Recommend regenerating
  `data/eval/copilot_questions.csv`** (delete it and let `run.py` recreate it, or
  rerun `make_copilot_questions`) so it reflects the current extraction, or drop
  this one row.

One borderline case, same pattern as the events-file disagreements: "Was there
overpressure in well 34/4-11?" → source text is "sandstones with oil shows and
drill gas peaks with a full C1-C5 chromatograph breakdown", which reads as a
routine hydrocarbon-show / mud-log description rather than a stated overpressure
incident. Not flagged as "unreasonable" outright since it does technically match
the taxonomy pattern, but it's the same reservoir-description-vs-drilling-event
ambiguity as pids 4017 and 36743 above.

## 4. Summary

| File | Rows checked | Ref drift | Agreement |
|---|---|---|---|
| events_gold.csv | 50 | 0 broken refs | 48/50 (96%) hazard agreement |
| episodes_gold.csv | 30 | 0 broken refs | 30/30 (100%) outcome agreement |
| copilot_questions.csv | 30 (25 answerable + 5 refusal) | 0 broken refs | 29/30 (97%) reasonable; 1 stale expected_source |

**Second pass by an AI model; not human-verified.**
