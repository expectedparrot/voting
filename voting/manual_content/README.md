# Editing the textbook

`manual.tex` assembles the chapters and references. These sources ship with
the package. Edit these packaged files, not a generated build.

The builder executes each `lstlisting` marked `style=votingrun`, in chapter
order. Use one complete voting command per line. The first command initializes
`study`; the builder then enters that directory. Listings marked
`style=votingerror` must return a structured validation error. Unmarked
listings, including external fielding examples, are explanatory only.

`voting.manual` exports the sources, runs the local CLI without a shell,
records envelopes, and generates LaTeX tables from saved results. The
manually specified profiles are fictional teaching data; no human, model,
or external service is used in a normal build.

Build into a new directory:

    voting docs manual --output-dir build/town-manual --pdf

Omit `--pdf` to run the examples and export LaTeX without TeX installed.
Use `--sources-only` to export an edition with explicit result placeholders.
Compilation uses pdflatex with shell escape disabled. Three passes resolve
the table of contents, bibliography, and chapter references.

Tests execute the source listings and check numerical claims, coverage
of all implemented counting functions, expected validation failures,
revision outcomes, and inclusion of the chapter files.
