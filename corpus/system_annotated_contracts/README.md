# Mbiu System Annotated Reference Contracts & Context Pipeline

> **Legal Expert Annotations & Dummy Contract Disclaimer**
> All reference contracts and clause-by-clause annotations in this pipeline were prepared and evaluated by a **legal expert** specializing in Kenyan entertainment, intellectual property, and music law, grounded in the Kenya Copyright Act (Cap. 130), the Performers Protection Act (Cap. 229A), the Kenya Copyright Board (KECOBO) Advisory Copyright Contract Manual, and WIPO reference guidelines.
>
> **Dummy Contracts Notice:** All contracts in this directory are **dummy contracts** prepared for system reference and context injection. All personal names have been switched out, the people mentioned (including **Amina Wanjiru** / `p/k/a "Mina W."` and all listed signatories or representatives) **do not exist**, and the companies, record labels, publishers, studios, and brands mentioned **either do not exist or have nothing to do with the contracts**.
>
> These legal-expert annotated contracts serve two core system functions:
> 1. **In-Memory API Context & Few-Shot Grounding:** Providing the Mbiu evaluation engine with verified legal reasoning, Kenyan statutory and industry standard benchmarks, and verified card structures during live evaluation API calls with zero disk I/O overhead.
> 2. **Future Model Fine-Tuning (SFT):** Providing a structured `.jsonl` corpus (`mbiu_context_and_finetuning_dataset.jsonl`) verified against all 8 of Mbiu's deterministic verification rules (`backend/mbiu/evaluation/verify.py`).

---

## Zero Data-Leakage Separation

To ensure rigorous evaluation integrity, these 6 system-annotated contracts are **100% distinct** from the 7 unannotated `John Doe` developer evaluation contracts in `evals/sample_contracts/`:
- They use a separate artist persona (**Amina Wanjiru**, `p/k/a "Mina W."`), different corporate/label counterparties, different song titles, and different financial figures.
- Every single annotated clause in this directory is programmatically verified against `verify_proposal()` from `backend/mbiu/evaluation/verify.py`.

---

## Directory Layout

- `markdown/` — The 6 annotated reference contracts in Markdown, pairing each contract clause with its `[EXPERT LEGAL & MBIU SYSTEM ANNOTATION]` block, plus Whole-Contract Map (`contract_map.issues`) and Reverse-Check (`missing_from_contract`) annotations.
- `pdf/` — Multi-page text-based PDFs rendered from the annotated Markdown files (with blue-accented callout blocks for the legal expert annotations).
- `mbiu_context_and_finetuning_dataset.jsonl` — Machine-readable JSON Lines dataset containing all extracted clause evaluations, reference standard chunks, expert tags, and verified Mbiu card fields.
- `generate_system_artifacts.py` — Script that renders the PDFs, builds the `.jsonl` file, and runs Mbiu's 8 Verification Rules (`verify_proposal`) across every clause.

---

## Summary of the 6 System Annotated Contracts

| Doc ID | File Basename | Contract Type | Counterparty | Risk / Teaching Profile |
| :--- | :--- | :--- | :--- | :--- |
| **`SYS-ANNOT-01`** | `sys_01_brand_endorsement_annotated_zuri_telecom` | `general_music` / `synchronization` (Brand Endorsement & Sync) | Zuri Telecom & Mobile Money Kenya Ltd | **Mixed / Hybrid Benchmark:** Teaches fine-grained discrimination within one contract (`matches_standard` on 50/50 KES 800k gross fee & Brand-paid production costs; `better_for_you` on 50% liability cap; `worse_for_you` on Clause 4.3 perpetual worldwide online override of the 6-month Term, 12-month multi-sector exclusivity, and 7-day convenience cancellation). |
| **`SYS-ANNOT-02`** | `sys_02_exclusive_recording_agreement_annotated_nyota_records` | `recording` (Exclusive Master Recording Deal) | Nyota Records & Entertainment East Africa Ltd | **Predatory Recording Deal vs. KECOBO/WIPO Standard:** Annotates open-ended Album-cycle options with no release deadline, perpetual `Work Made for Hire` master assignment vs. 7-year license / post-recoupment reversion, 5% Net Digital/Skiza royalty after 20% packaging & 15% free-goods deductions, 100% artist-share recoupment + cross-collateralization, 75% Controlled Composition cap, and Clause 7.2 override suspending all statements while unrecouped. |
| **`SYS-ANNOT-03`** | `sys_03_music_publishing_copub_annotated_simba_publishing` | `publishing` (Songwriter & Co-Publishing Deal) | Simba Music Publishing & Sync Admin Ltd | **Predatory Publishing Grab vs. Admin Standard:** Annotates 100% perpetual copyright assignment vs. 3-year Administration / 50-50 Co-Pub standard, fractional co-write delivery quotas (15 full songs = 30 co-writes/year), "Receipts in Kenya" double-deduction (50% foreign sub-publisher + 20% admin fee before 50/50 split) vs. "At Source" gross royalties, unapproved political/commercial sync licensing, and Clause 5.2 override blocking song reversion and seizing the MCSK Writer's Share. |
| **`SYS-ANNOT-04`** | `sys_04_artist_management_agreement_annotated_elevate_mgmt` | `management` (Personal Artist Management Deal) | Elevate Talent Management Ltd | **Exploitative Management Deal vs. KECOBO/MMF Standard:** Annotates 8-year lock-in without income targets or a Key-Man clause, 25% commission on Gross Receipts (including recording budgets, video funds, and live band/sound pass-through costs) vs. 15%–20% on Net Receipts, perpetual 25% post-term Sunset Commission vs. 2-year stepped sunset, uncapped expenses, and Power of Attorney / general bank account commingling. |
| **`SYS-ANNOT-05`** | `sys_05_producer_split_agreement_annotated_fair_standard` | `producer` (Studio Production & Split-Sheet Deal) | Boma Sound Labs Ltd ("Kazi Beats") | **Gold-Standard Fair Benchmark (`matches_standard` & `better_for_you`):** Teaches the system to recognize a fair Kenyan studio deal without false alarms: KES 60,000 gross fee (50% on booking, 50% on WAV + stems delivery), 100% Master copyright owned by Artist, exclusive beat covenant, 4% gross producer royalty after recoupment, 50/50 songwriting Split Sheet for MCSK/KECOBO, and Producer sample-clearance warranty & indemnity. |
| **`SYS-ANNOT-06`** | `sys_06_live_performance_booking_annotated_afribeat_live` | `live_performance` (Festival & Concert Booking) | AfriBeat Live Experiences Ltd | **Mixed Live Performance Benchmark:** Contrasts fair pre-stage settlement (50% deposit + 50% paid 2 hours before stage walk-on) and Force Majeure deposit retention (`matches_standard`) against a 90-day countrywide blackout covering private corporate/wedding gigs and perpetual uncompensated pay-per-view livestream + sponsor commercial capture waiving Section 30 Performer's Rights (`worse_for_you`). |

