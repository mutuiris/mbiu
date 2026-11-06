# Corpus sources research

Agent-reported findings from browser checks on 30 October and 6 November 2026. This is not legal advice.

## Added to the corpus

| Source | Licence | Content | Date checked |
|---|---|---|---|
| World Intellectual Property Organization (WIPO), *How to Make a Living from Music*, third edition (2024) | CC BY 4.0 | Annex A (short-term management letter of engagement and expenses schedule) and Annex B (long-form artist-management agreement and schedule) | 2026-10-30 |
| Kenya Copyright Board (KECOBO), Music License Agreement, Recording/Producer Agreement and Deed of Assignment | CC-BY SA, version not stated | Three fill-in-the-blank contract templates | 2026-11-06 |

WIPO citation: World Intellectual Property Organization (WIPO) (2024). *How to Make a Living from Music*, third edition. Geneva: WIPO. DOI 10.34667/tind.45019. The licence conditions require credit to WIPO, an indication of changes, WIPO's disclaimer for derivatives, and no use of the WIPO emblem or logo.

KECOBO's licence comes from the site footer, which also excludes material specifically attributed to others. The PDFs carry no licence line of their own. The team still has to confirm the licence version and how ShareAlike applies to adapted text.

## Pending a team decision

| Source | Licence | Why it is not in `sources.yaml` |
|---|---|---|
| J DuClos LLC, Master Use & Sync License Agreement | CC0 1.0 Universal | The schema requires a `reviewing_body`, and no named reviewing body exists. The agreement is also drafted for US practice and uses US terminology. |

## Rejected or blocked sources

| Source | Reason |
|---|---|
| Kenya Law / NCLR | Raw documents are CC BY-NC 4.0; the terms prohibit scraping and AI training without an agreement. |
| Music In Africa | Site content is CC BY-NC; non-commercial use only. |
| AI Lawyer | The site advertises CC BY-SA 4.0, but its licence page excludes all legal document templates. |
| Genie AI | No open licence; the site says "all rights reserved". |
| Goethe-Institut | A real, populated South African publishing contract with personal data and no licence. |
| MCSK | No verified reusable licence found. |
| PAVRISK | The site returned a bot challenge; its official name and licensing contact could not be verified, and no reusable licence was confirmed. |
| KAMP | No verified reusable licence found. |
| Strathmore CIPIT | No verified reusable licence found; a permission request is pending. |
| Music and Film Academy | No verified reusable licence found; a permission request is pending. |
| Musicians' Union (UK) | Useful specimen agreements, but no licence is stated; a permission request is pending. |
| NZ Music Commission | Useful Basic Performance Agreement, but no licence is stated; a permission request is pending. |
| Creative New Zealand | Guidance only, no template, and no licence is stated. |

Also reviewed and not usable: Arts Law Centre of Australia (paid), APRA AMCOS (paid), ISM (members only), Making Music (no licence), Music Victoria (robots.txt blocks AI crawlers), and Live Music Office (site did not connect).

## Coverage gap

No usable open-licensed templates were found for music publishing, brand partnership, performance/booking, distribution, label recording deals, or 360 deals. KECOBO publishes guidance on some of these topics, but not templates.

## Schema notes

`corpus/sources.yaml` supports only `url`, `licence`, `reviewing_body`, `contract_type`, `jurisdiction` and an optional `template_version`. It has no field for title, publisher, DOI, language, date checked, reuse conditions, permission contact or NC/ND flags, so those details are recorded here. `template_version` was left unset so the loader's default (`"1"`) applies; the WIPO edition is identified by its URL and citation above.
