# Related Work and Similar Projects

Version 0.1 · 2026-10-23 · Living document, updated as papers are read

The advisor asked for the closest related work and for similar projects that already exist
(meeting of 23 October 2026). This file lists them with links and short descriptions so they
can be followed from the repository. Full texts are not stored here: publishers' PDFs are
copyrighted, so only links are given; open-access versions are linked where they exist. The
literature search itself (search log, themes, reading notes) is kept in the reference manager.

Research questions the literature serves (from the proposal):
- **AS1** Does a hybrid approach (vision-language model + rule engine) find missing and
  inconsistent documents in multi-document application files better than an LLM-only approach?
- **AS2** How does the hybrid system compare with human reviewers in accuracy and time?
- **AS3** How accurately does source monitoring separate meaningful requirement changes from
  cosmetic page changes?

## 1. Academic work

Status: **read** = read in full with notes; **to read** = abstract checked, full reading planned.
Preprints are marked; a peer-reviewed version is cited instead once it exists.

### 1.1 Closest to the project
| Work | Why it matters | Question | Status |
| --- | --- | --- | --- |
| Chen, S., Fan, W., Jin, R., Ma, K. (2026). *Detecting Contradictions Within and Across Documents.* Proc. ACM Manag. Data 4(4), Art. 267. [doi:10.1145/3837105](https://doi.org/10.1145/3837105) (open access) | DocChecker combines an entity–relation graph and logic rules with ML/NLP to find contradictions within and across documents; average F1 about 0.90. The closest hybrid design to ours, so the report must state the difference: we check documents against **external, versioned official requirements** and against each other, on a fixed set of document types with field-level rules. | AS1 | to read (first) |
| Selch, L. et al. (2025). *PRISMM-Bench: A Benchmark of Peer-Review Grounded Multimodal Inconsistencies.* [arXiv:2510.16505](https://arxiv.org/abs/2510.16505) (preprint) | 21 multimodal LLMs find real inconsistencies in scientific papers with only about 28–54 % accuracy: evidence that an LLM-only baseline is likely to struggle on cross-document consistency. | AS1 | to read |
| Mallawaarachchi, V. et al. (2020). *Change Detection and Notification of Web Pages: A Survey.* ACM Computing Surveys 53(1), Art. 15. [arXiv version](https://arxiv.org/abs/1901.02660) | Main survey for AS3: change detection methods, crawling schedules, notification. | AS3 | to read |

### 1.2 Document understanding and extraction (spring, FR-12, FR-13)
| Work | Note | Status |
| --- | --- | --- |
| Ding, Y. et al. (2026). *A Survey on MLLM-based Visually Rich Document Understanding.* Findings of ACL 2026, 13319–13340. [doi:10.18653/v1/2026.findings-acl.652](https://doi.org/10.18653/v1/2026.findings-acl.652) | Most recent survey of multimodal-LLM document extraction. | to read |
| Cui, L., Xu, Y., Lv, T., Wei, F. (2021). *Document AI: Benchmarks, Models and Applications.* [arXiv:2111.08609](https://arxiv.org/abs/2111.08609) (preprint) | Overview of benchmarks (FUNSD, CORD, DocVQA) and layout models. | to read |
| Huang, Y. et al. (2022). *LayoutLMv3.* ACM Multimedia; Kim, G. et al. (2022). *Donut: OCR-free Document Understanding Transformer.* ECCV | Named in the proposal; Donut's SynthDoG is a reference for synthetic document generation (FR-22). | to read |
| Livathinos, N. et al. (2024). *Docling Technical Report.* [arXiv:2408.09869](https://arxiv.org/abs/2408.09869) | Open-source document conversion toolkit (also a candidate component, see 3). | to read |

### 1.3 Name matching across documents (FR-09 name rule)
| Work | Note | Status |
| --- | --- | --- |
| Christen, P. (2006). *A Comparison of Personal Name Matching: Techniques and Practical Issues.* ICDM Workshops. [doi:10.1109/ICDMW.2006.2](https://doi.org/10.1109/ICDMW.2006.2) | No single technique wins on all data sets; basis for normalising names before comparison (Turkish characters, order of given names). | to read |

### 1.4 LLM limits, retrieval and citation (FR-15, AS1 baseline)
| Work | Note | Status |
| --- | --- | --- |
| Ji, Z. et al. (2023). *Survey of Hallucination in Natural Language Generation.* ACM Computing Surveys 55(12). [doi:10.1145/3571730](https://doi.org/10.1145/3571730) | Why confident answers without sources are a risk (positioning, section 2.5). | to read |
| Gao, Y. et al. (2024). *Retrieval-Augmented Generation for Large Language Models: A Survey.* [arXiv:2312.10997](https://arxiv.org/abs/2312.10997) (preprint) | Design space for the assistant. | to read |
| Gao, T., Yen, H., Yu, J., Chen, D. (2023). *Enabling Large Language Models to Generate Text with Citations (ALCE).* EMNLP 2023. [ACL Anthology](https://aclanthology.org/2023.emnlp-main.398/) | Metrics for citation quality; used to evaluate assistant answers against LLM-only answers. | to read |

### 1.5 Change detection (AS3)
| Work | Note | Status |
| --- | --- | --- |
| Zhang, S., Dyreson, C., Snodgrass, R. T. (2004). *Schema-Less, Semantics-Based Change Detection for XML Documents.* WISE 2004, LNCS 3306. [doi:10.1007/978-3-540-30480-7_29](https://doi.org/10.1007/978-3-540-30480-7_29) | Semantic rather than textual diff; idea for separating meaningful from cosmetic changes. | to read |

## 2. Similar projects

Searched on 23 October 2026 (web search for open-source visa and document-check assistants).
None of the projects reports an evaluation with accuracy figures.

| Project | What it does | Approach | Official sources | License | Adopt / differ |
| --- | --- | --- | --- | --- | --- |
| [VISAPATH](https://github.com/sankeerthanayerubandi-gif/VISAPATH) | Completeness and cross-document consistency checker for visa documents; states it does not predict approval | Streamlit, Chroma retrieval, OpenAI, Pydantic reports, LLM-as-a-judge, prompt-injection scan | Not named | None stated | Closest in goal. Idea to adopt: **prompt-injection scanning of uploaded documents** before any LLM call. Differ: our rules are explicit, cite sources and are tested; we measure accuracy. |
| [UK Visa Auditor](https://github.com/taimoorcodes-cmd/uk-visa-auditor) | Checks UK student visa documents (passport MRZ, CAS, bank statements), 28-day funds rule | LangGraph, JSON rules engine, Tesseract, RapidFuzz | gov.uk links in chat | None stated | Confirms the rules + OCR + fuzzy matching pattern. Idea: **MRZ parsing** of the passport as a cheap, exact source for name, number and dates. |
| [Visa-Agent](https://github.com/Sanssssssssssssssss/Visa-Agent) | Email-first assistant that keeps a UK visa case across messages, asks for missing items, delivers a ZIP pack | PydanticAI proposes facts; Python does rule checks and state; versioned rule snapshots; model cannot approve a case | Not clearly documented | MIT | Same principle as ours: **LLM proposes, rules decide**. Ideas: blocking "unresolved checks", bilingual worksheet, export of the application pack. |
| [visa-assistant](https://github.com/Udit-takkar/visa-assistant) | Local Schengen research assistant answering from reviewed Reddit threads with cited quotes | Next.js, pgvector + full-text hybrid retrieval (reciprocal rank fusion), local Qwen; validates citation IDs | Reddit, official sources "later work" | None stated on page; third-party notices included | Idea: **hybrid retrieval with reciprocal rank fusion** in pgvector for FR-15. Differ: official sources only. |
| [Schengen-master](https://github.com/torlyai/Schengen-master) | Toolkit for a family Schengen (France) application; Chrome extension watching appointment slots; document templates | TypeScript extension, Markdown skills | — | MIT | Appointment watching is out of our scope (no booking on the user's behalf); templates idea fits the consulate e-mail drafts. |
| [changedetection.io](https://github.com/dgtlmoon/changedetection.io) | Mature web page change monitor (about 34k stars) | Python; selector filters, ignore rules, text and PDF diff, notifications, optional LLM change summaries | — | Apache-2.0 | Reference for AS3: **CSS/XPath filtering and ignore rules** to drop menus and scripts; its text diff is a natural AS3 baseline. Our part: link a change to the rules it affects and to the applicants. |
| [Ballerine](https://github.com/identome/ballerine) (fork of ballerine-io/ballerine) | Open-source KYC/KYB identity and risk workflows | Web/mobile SDKs for document collection; rule engine marked work in progress | — | Check LICENSE file | Shows the document-collection flow of a KYC product; little to reuse directly. |

**What none of them does:** tie each requirement to a versioned official source passage, detect
when that source changes, and notify only the applicants whose files the change affects; or
report measured error rates against an LLM-only baseline and human reviewers. These are the
project's contributions (`docs/positioning.md`).

## 3. Open-source components we may use

| Component | Use | License | Status |
| --- | --- | --- | --- |
| Tesseract OCR | OCR fallback (ADR 0002) | Apache-2.0 | planned (spring) |
| RapidFuzz | Fuzzy name comparison after normalisation | MIT | candidate for the name rule (W12) |
| Docling | PDF and image to structured text before extraction | MIT | candidate (spring) |
| changedetection.io | Ideas only (filters, ignore rules); not embedded | Apache-2.0 | reference for AS3 |
| pgvector | Vector search in PostgreSQL | PostgreSQL License | in use (Docker image) |

## 4. Reuse policy
- Code under MIT, Apache-2.0 or BSD can be adapted; the source and license are recorded in
  `THIRD_PARTY.md` when the first piece is taken.
- GPL code is not copied into the project, because it would change the project's license.
- Code without a license is not copied; only the idea is reused and implemented anew.
- A published system without code is reimplemented from its description, and cited.
