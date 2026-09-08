# Textbook and Extended Example

**One Town, Many Ways to Choose** is a LaTeX textbook and manual, following
a fictional town through ranked elections, committees, scores, grades,
quadratic voting, and the Method of Equal Shares.

```bash
voting docs manual --output-dir town-manual --pdf
```

Use a new directory for each build. No existing voting project is required.
The build exports the packaged chapter sources, executes their local command
listings in an isolated `study/` project, and generates tables from actual
CLI results. It does not contact external services or execute language models.
All ballot profiles are explicitly invented teaching data.

The book includes notation, formulas, algorithm descriptions, hand calculations,
generated result tables, plots, exercises, selected answers, references,
and a complete command transcript. It describes implementation conventions
for ties, incomplete ballots, weighted quotas, and equal-shares completion.

If TeX is unavailable, omit `--pdf`; examples and generated LaTeX still work.
`--sources-only` exports sources without executing examples. It can be combined
with `--pdf` to make an explicitly labeled source-only edition.

PDF compilation needs `pdflatex` and the packages in `manual.tex`, including
Latin Modern, PGFPlots, and xurl. Compilation disables shell escape and runs
three passes. Inspect `manual.log` if compilation fails; generated files remain
available for diagnosis.

Outputs:

- `manual.pdf` when requested, and editable `manual.tex` plus chapter sources.
- `commands.json`: actual commands, expected-error markers, and JSON envelopes.
- `results.json`: saved count results from the examples.
- `generated/`: numerical LaTeX tables, plot coordinates, and readable transcript.
- `study/.voting/`: the ordinary project used for the examples.
- `build-manifest.json`: version, build mode, and command/result counts.

Source-only exports omit the study, command ledger, and numerical outputs.
They never substitute invented results for an unexecuted build.

For permanent edits, change `voting/manual_content/` in the source checkout.
Listings marked `style=votingrun` execute; `style=votingerror` must fail with
a structured error. One complete command belongs on each source line, even
when LaTeX wraps it visually. Other listings are explanatory examples only.
