# Report (LaTeX)

Source of the CMPE 491/492 report. It is edited on Overleaf and kept here as the versioned copy.

- **Compile:** Overleaf, compiler *pdfLaTeX*, bibliography tool *Biber* (Menu → Settings).
- **Citations:** Chicago author-date (`biblatex-chicago`). Cite with `\autocite{key}` →
  (Author Year), or `\textcite{key}` → Author (Year).
- **References:** `references.bib`; replace it with the Better BibTeX export of the Zotero
  collection "VisaAssist AI" once that is set up (keep the citation keys).
- **Structure:** `main.tex` (preamble and order), `frontmatter/`, `chapters/`, `appendices/`,
  `figures/` (exported from `docs/design/ui/`).
- **Placeholders:** `\todo{...}` prints orange text; none may remain at submission
  (`grep -rn '\\todo' report/`).
- **Official template:** when the department's "Senior Design Project Final Report" template is
  available, move the chapter files into it; they do not depend on this preamble.
- **Sync with Overleaf:** download the project as a zip from Overleaf and copy the changed files
  here in a pull request (or use Overleaf's GitHub sync, if available on your plan).
