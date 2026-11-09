# Mbiu Reference Standards, Guidelines & Statutory Acts Compendium

> **Authoritative Legal & Industry Benchmarks for Mbiu Contract Evaluation**
> This directory contains the statutory provisions, regulatory contract manuals, and international music-industry reference standards used by **Mbiu** to evaluate music contracts for Kenyan recording artists, songwriters, producers, and performers.

---

## Included Standards, Guidelines & Statutes

1. **Kenya Copyright Act (Cap. 130, Laws of Kenya)**
   - **Section 22 & 26:** Eligibility and exclusive economic rights in musical works (reproduction, distribution, translation, adaptation, broadcasting, and communication to the public).
   - **Section 28:** Exclusive rights of producers of sound recordings (masters).
   - **Section 30:** Exclusive rights of performers in their live performances and fixations.
   - **Section 30A:** Statutory right to a single equitable remuneration for performers and producers when a sound recording published for commercial purposes is used directly for broadcasting or other communication to the public (including Skiza Tunes and public broadcast).
   - **Section 32 (Moral Rights):** Independently of the author's economic rights, and even after the transfer of those rights, the author retains the right to claim authorship of the work (*paternity*) and to object to any distortion, mutilation, or other modification of the work that would be prejudicial to the author's honour or reputation (*integrity*). Moral rights are not transmissible during the life of the author.
   - **Section 33 (Assignments & Exclusive Licenses):** No assignment of copyright and no exclusive license to do an act controlled by copyright shall have effect unless it is in writing signed by or on behalf of the assignor or licensor, and a certificate of registration is issued by the Kenya Copyright Board (KECOBO) where applicable.
   - **Section 46 (Collective Management Organizations):** Supervision and licensing of CMOs (such as MCSK, KAMP, and PRISK) by KECOBO for collection and distribution of royalties.

2. **Performers Protection Act (Cap. 229A, Laws of Kenya)**
   - Protects performers against unauthorized fixation, recording, broadcasting, livestreaming, or commercial exploitation of their live performances without prior written consent and fair remuneration.

3. **Kenya Copyright Board (KECOBO) Advisory Copyright Contract Manual & Standard Templates**
   - **Exclusive Recording & 360 Agreements:** Fair royalty baselines (15%–20% of wholesale/gross receipts or 50/50 net profit split), prohibition of artificial digital packaging/container deductions and free-goods deductions on streams, recoupment strictly from the Artist's recording royalty share (no cross-collateralization against mechanicals or live performance income), guaranteed album release within 6–12 months of delivery, and master rights reversion after recoupment or a fixed license term (5–7 years).
   - **Studio Producer, Beat Lease & Split-Sheet Agreements:** Clear distinction between studio engineering/session hire (where the Artist paying the session fee owns 100% of the Master) and co-production; mandatory execution of a Songwriting & Master Split Sheet for KECOBO/MCSK registration; 3%–5% producer royalty points after recoupment; and producer warranty that beats contain no uncleared third-party samples.
   - **Brand Partnership, Influencer Endorsement & Commercial Synchronization Agreements:** 50% mobilization deposit upon signing and 50% within 14–30 days of delivery on a Gross Fee basis; 100% Brand responsibility for production, agency, and ad-boosting expenses; fixed campaign Term and Territory license (no perpetual copyright assignment or Work-for-Hire grab); narrow product-category exclusivity during the active Term only; and preservation of Moral Rights and prohibition on unauthorized AI voice cloning ("Digital Twin" training).
   - **Digital Distribution & Telecom Ringback Tone (Skiza Tunes / Hello Tunes) Aggregation Agreements:** Artist retains 100% copyright ownership of Masters and Compositions; Artist receives 80%–90% of Gross Digital Receipts from DSPs (Spotify, Apple Music, Boomplay, Mdundo, YouTube) and Net Telecom Receipts after statutory operator retention; monthly accounting statements; and 30–60 day termination notice with 14-day DSP takedown.

4. **WIPO Reference Standards (*How to Make a Living from Music*, 3rd Ed., CC BY 4.0) & International Creator Organization Baselines (MMF / FAC / UK Musicians' Union / CISAC)**
   - **Personal Artist Management Standards:** Commission of 15%–20% on Net Entertainment Receipts; exclusion of recording budgets, video production funds, and live sound/touring pass-through expenses from commission; 3-year initial term with objective income/career performance benchmarks; Key-Man clause ensuring personal service by the named manager; stepped post-term Sunset Commission (e.g., 10% in Year 1, 5% in Year 2, 0% thereafter) strictly on contracts entered into during the Term; and separate trust account handling with annual CPA(K) audit rights.
   - **Music Publishing & Co-Publishing Standards:** Calculation of royalties **"At Source"** rather than after multi-territory sub-publisher deductions; strict preservation of the 50% **Writer's Share** paid directly to the songwriter by their CMO (MCSK); 3–5 year Administration term or post-recoupment retention window; 24-month exploitation deadline with automatic reversion of unexploited compositions; and prior written songwriter consent for political, religious, alcohol, tobacco, gambling, or AI-training synchronization uses.
   - **Live Performance & Festival Booking Standards:** 50% non-refundable deposit upon signing and 50% balance prior to stage performance; Artist retains deposit upon Promoter or Force Majeure cancellation; radius blackout limited to public ticketed concerts within 30–50 km and 30–60 days (excluding private weddings and corporate functions); and separate written license and fee required for commercial VOD/pay-per-view broadcast or sponsor advertising sync.

5. **Kenyan Tax, Data Protection & Dispute Resolution Statutes**
   - **Income Tax Act (Cap. 470, Laws of Kenya):** 5% resident Withholding Tax on royalties and professional/contractual/management/agency fees, accompanied by a mandatory KRA iTax Withholding Tax Certificate within 14 days.
   - **Data Protection Act (No. 24 of 2019, Laws of Kenya):** Explicit informed consent required before processing biometric, vocal, or likeness data for automated profiling or AI voice synthesis.
   - **Arbitration Act (Cap. 49) & Nairobi Centre for International Arbitration (NCIA) Rules:** Dispute resolution via good-faith negotiation, NCIA mediation, and Kenyan courts in Nairobi governed by the laws of the Republic of Kenya.

---

## How Mbiu Uses These Standards at Runtime

1. **Corpus Pipeline (`corpus/sources.yaml` & `backend/mbiu/corpus/pipeline/runner.py`):**
   All 10 sources and 32 operative standard clauses are structured in `corpus/sources.yaml` and validated by Mbiu's 6 automated quality checks (`metadata_validation`, `template_validation`, `pii_scan`, `language_check`, `deduplication`, and `tag_consensus`).
2. **Zero-Latency In-Memory Snapshot (`backend/mbiu/corpus/loader.py`):**
   Both the database-backed `CorpusSnapshot` and the built-in in-memory fallback snapshot (`get_fallback_or_active_corpus_snapshot()`) hold these standards in memory alongside the 37 legal-expert annotated contract exemplars (`get_annotated_exemplars()`), guaranteeing `< 1 ms` retrieval during API calls with zero disk or database I/O on the request path.

