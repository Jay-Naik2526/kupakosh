# Well Wiki bundle format

Google's "Open Knowledge Format v0.1" could not be verified from the build session, so this is our own
format, kept close to common Markdown-knowledge-base conventions.

```
wiki/                      (its own git repository; every compile and review = a commit)
  index.md                 list of pages: [[slug]] title — ref_no vN (status)
  hazards/<key>.md         one per taxonomy hazard
  formations/<slug>.md     one per formation with at least one trusted event
  wells/<slug>.md          one per well with trusted events (+ all FORGE wells)
```

Each page = YAML frontmatter + Markdown body:

```yaml
---
id: formations/hugin-fm
kind: formation                 # formation | hazard | well | lesson
ref_no: KPK/WIKI/FRM/0032
version: 1
title: Hugin Fm
status: draft                   # draft | in_review | approved | returned
trust: 0.667                    # share of cited report lines with no open audit conflict
sources: [query:formation_top?formation=HUGIN+FM, doc:594#p5.s3, ...]
approved_by: R. Das             # only after approval
approved_at: 2026-09-26
compiled_at: 2026-09-24T12:49:07+00:00
---
## Summary
Hugin Fm has a formation top recorded in 140 documented wells in this dataset. [^s1]
> "At 3602 m, during coring, a water kick was detected." — 25/2-15 R2 [^s3]

[^s1]: query:formation_top?formation=HUGIN+FM
[^s3]: doc:594#p5.s3
```

Rules enforced by `app/wiki/compiler.py`:
- every content line ends with `[^sN]`; `check_citations()` rejects the page otherwise (also on reviewer edits);
- every number in a sentence must appear in its structured facts or in the cited source text;
- links between pages use `[[slug]]`;
- sections: Summary · Known hazards · What worked · Casing & cement notes · Related wells.
