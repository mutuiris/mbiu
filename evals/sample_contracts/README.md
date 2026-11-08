# Mbiu Evaluation Sample Contract Suite (`John Doe`)

> **Synthetic test contracts.** Written to test the **Mbiu** contract analysis pipeline. They are not real
> agreements and are not legal advice.
>
> All people, companies, labels, brands, studios and festivals are invented or have nothing to do with these
> contracts. The artist alias **John Doe** (`p/k/a "John Doe"`) and every signatory do not exist.

---

## Directory Structure

- `markdown/` — Full source text of the 7 contracts in readable Markdown format.
- `pdf/` — Text-based multi-page PDF versions of the 7 contracts (ready for direct upload to Mbiu's web UI or `/api/v1/evaluations` endpoint).
- `generate_pdfs.py` — Script using `pymupdf` to compile the Markdown contracts into paginated A4 PDFs.

---

## Overview of the 7 Evaluation Contracts

The suite spans **four contract categories** that frequently expose Kenyan musicians to financial or intellectual property exploitation (**Brand Partnerships**, **360-Degree Recording/Management/Publishing Deals**, **Digital Distribution & Skiza Aggregation**, **Studio Producer/Beat Agreements**, and **Live Performance/Festival Gigs**), varied systematically across **three exploitation tiers** and **document lengths** (from a deceptively short 2-page studio contract to a dense multi-page 360 deal with three Schedules).

| # | File Basename | Contract Type | Counterparty | Exploitation Tier | Approx. Length | Key Evaluation Focus |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | `01_brand_partnership_fair_savannah_mobile` | Brand Partnership / Endorsement | Savannah Mobile Ltd | **Tier 1: Zero / Minimal Exploitation** (Balanced Standard) | Medium (~4 pages, 12 clauses + Schedule 1) | Verifies no false alarms: `matches_standard` & `better_for_you` ("Good news") on 100% IP retention, 50/50 gross payment, narrow handset-only 3-month exclusivity, mutual termination, and Kenyan law. |
| **02** | `02_brand_partnership_unusual_kibo_beverages` | Brand Partnership / Sync & Jingle | Kibo Beverages East Africa Ltd | **Tier 2: Unusual / Moderately Exploitative** | Medium-Long (~5 pages, 12 clauses + Schedule A) | Tests detection of `worse_for_you` & cross-clause override: 15% "Agency Deduction", 80% paid Net-90, perpetual social/YouTube archive rights, 24-month commercial holdback overriding Clause 5.1 ownership, beverage + club/festival sponsor exclusivity + 6-month Cooling-Off Period, and subjective morality clawback. |
| **03** | `03_brand_partnership_exploitative_apexpesa` | Brand Partnership / Sync, Merch & AI Digital Twin | ApexPesa Global Gaming & Entertainment Ltd | **Tier 3: Severely Exploitative** (Predatory) | Long (~6 pages, 14 dense clauses + Schedule 1) | Tests severe `worse_for_you`, `missing_from_contract`, and **2 planted cross-clause overrides**: (1) Clause 3.1 promises KES 1.2M fee, overridden by Clause 14.2/14.3 making 75% contingent on 250,000 betting conversions and making all production/ad costs 100% recoupable; (2) Work-for-Hire perpetual assignment + capture of pre-existing songs performed at events (Clause 5.5), AI voice cloning ("Digital Twin Rights"), total Moral Rights waiver, KES 5M liquidated damages, waiver of audit rights, and London LCIA arbitration under English law. |
| **04** | `04_360_recording_deal_exploitative_lengthy_vanguard` | 360-Degree Recording, Co-Publishing & Management | Vanguard Sound & Vision Label Group Ltd | **Tier 3: Severely Exploitative & Very Lengthy** | Very Long (~10 pages, 23 clauses + 3 Schedules) | Tests lengthy-contract handling, impact ordering, token budgets, music jargon explanation, and cross-clause overrides: Initial Period + 5 unilateral Option Periods tied to MDRC (up to 10 Albums), perpetual Master assignment *ab initio*, 12% Net Receipts reduced by 25% Container Charge, 15% Free Goods, 50% Digital/Skiza cut (effective 6% Net), 35% Reserves held 4 years, 100% recoupment of video/marketing/tour costs from Artist share + full Cross-Collateralization, 35% passive 360 cut + 20% management fee + 5-year 25% Sunset Commission, 50% Co-Publishing grab + 75% Controlled Composition rate (10-track cap), CMO redirection (MCSK/KAMP/PRISK), KES 500k audit deposit precondition, and Clause 22 override suspending all statements/payouts while unrecouped and seizing pre-existing catalogue. |
| **05** | `05_digital_distribution_fair_mashariki` | Digital Distribution & Skiza Aggregation | Mashariki Digital Distribution Ltd | **Tier 1: Zero / Minimal Exploitation** (Artist-Friendly) | Medium (~4 pages, 9 clauses + Schedule 1) | Tests positive baseline for distribution: Artist retains 100% Master & Composition copyright and Moral Rights, 85% of Gross Digital Receipts (Spotify/Boomplay/Mdundo/Apple Music) and 80% of Net Telecom Receipts (Skiza Tunes), zero packaging/container or free-goods deductions, monthly statements & M-Pesa payouts, CPA(K) audit right (5% error threshold), and 60-day opt-out with 14-day takedown. |
| **06** | `06_producer_beat_agreement_exploitative_short_kronik` | Studio Producer, Beat Lease & Master Split | Apex Beats Productions Ltd (d/b/a "DJ Kronik Studios") | **Tier 3: Severely Exploitative (Deceptively Short)** | Short (~2–3 pages, 7 clauses) | Tests the classic "Nairobi studio trap": Artist pays KES 45,000 session fee, yet Clause 3.1 assigns 100% of the Master copyright to the Producer as a reverse "Work Made for Hire" + 75% of Publishing, while keeping the beat non-exclusive (Producer can resell the beat and mute/replace Artist's vocals). Clause 6.2 overrides Clause 2.2 by barring Artist from uploading the song and letting Producer keep 100% of the first KES 300,000 ("Discounted Beat Subsidy"). |
| **07** | `07_live_performance_unusual_rift_valley_festival` | Live Performance, Festival & Broadcast Capture | Rift Valley Live Events & Promotions Ltd | **Tier 2: Unusual / Moderately Exploitative** | Medium (~3–4 pages, 9 clauses) | Tests gig/festival risks: KES 180,000 fee with only 10% deposit, and Clause 3.3 overriding the 90% balance unless festival hits 2,000 paid gate attendees; 25% fee deduction per 15 mins late to 7:00 AM soundcheck; 100 km / 105-day radius blackout across Nairobi & Nakuru; perpetual uncompensated live recording & sponsor commercial sync license; 40% venue merch cut; and rain/permit cancellation clawback of deposit. |

---

## Planted cross-clause conflicts and overrides

| Contract | Primary Clause | Overriding / Conflicting Clause | Nature of Conflict / Override |
| :--- | :--- | :--- | :--- |
| **02 (Kibo Beverages)** | **Clause 5.1** (Artist retains nominal copyright in underlying musical composition of the Campaign Anthem) | **Clause 5.4** (*"Notwithstanding Clause 5.1 or anything to the contrary..."*) | Bars John Doe from releasing, performing live, or monetizing the song or any similar melody for 24 months post-term, while Clause 5.3 grants a perpetual worldwide digital archive license. |
| **03 (ApexPesa)** | **Clause 3.1** (Promises a Headline Sponsorship Fee of KES 1,200,000) | **Clause 14.2 & 14.3** (*"Notwithstanding Clause 3.1 or anything to the contrary in Schedule 1..."*) | Makes 75% of the fee (KES 900,000) contingent on 250,000 depositing betting sign-ups within 90 days, AND makes 100% of production, video, and ad-boosting costs recoupable from the Artist's fee. |
| **03 (ApexPesa)** | **Clause 5.1** (Defines Campaign Works as newly created campaign deliverables) | **Clause 5.5** (*"Notwithstanding Clause 5.1..."*) | Automatically captures any pre-existing or independent song performed or teased by John Doe during any Brand roadshow or livestream into perpetual royalty-free sync + 50% publishing assignment. |
| **04 (Vanguard 360)** | **Clause 6.1, 7.2 & 9.1** (12% Net Receipts royalty, 65% Artist share of Ancillary Income, semi-annual statements within 90 days) | **Clause 22.2** (*"Notwithstanding Clause 6.1, Clause 7.2, or Clause 9.1..."*) | Suspends all semi-annual accounting statements and royalty/ancillary payouts indefinitely whenever the consolidated cross-collateralized Advance account is unrecouped or accrued royalties are under KES 250,000, diverting 100% of Artist's live/endorsement share to recoupment. |
| **04 (Vanguard 360)** | **Clause 2.1 & 4.1** (Applies to Masters recorded during the Term) | **Clause 22.3** (*"Notwithstanding Clause 2.1 or Clause 4.1..."*) | Seizes perpetual copyright ownership of John Doe's entire pre-existing back catalogue recorded prior to the Effective Date as "collateral security." |
| **06 (DJ Kronik Producer)** | **Clause 2.2** (Upon payment of KES 45,000 Session Fee, Producer delivers WAV/MP3 mix for Artist's promotional use) | **Clause 6.2** (*"Notwithstanding Clause 2.1, Clause 2.2..."*) | Prohibits Artist from uploading the track to YouTube, DSPs, or Skiza Tunes, and allows Producer to retain 100% of the first KES 300,000 in revenue as a "Discounted Beat Subsidy." |
| **07 (Rift Valley Festival)** | **Clause 3.1 & 3.2(b)** (Headline Performance Fee of KES 180,000 with 90% balance of KES 162,000 paid within 30 business days) | **Clause 3.3** (*"Notwithstanding Clause 3.1 or Clause 3.2(b)..."*) | Converts the 90% balance from a guaranteed flat fee into 5% of "Net Box Office Profits" (after all festival and international headliner costs) if paid attendance is under 2,000 tickets. |

---

## Music-business and legal jargon planted to test plain-language explanations

These contracts deliberately incorporate dense music-business and Kenyan legal terminology to test Mbiu's plain-language explanations:
- **Financial & Royalty Jargon:** *Gross Receipts*, *Net Receipts*, *All-In Royalty*, *Recoupable Advance*, *Double-Dip Recoupment*, *Cross-Collateralization*, *Container / Packaging and Infrastructure Charge*, *Free Goods Allowance*, *Reserves Against Returns*, *Sunset Commission*, *Passive 360 Share*, *Net-90 Payment*, *Liquidated Damages*, *Hall Fee / Merch Concession*.
- **Copyright & IP Jargon:** *Ab Initio*, *In Perpetuity Throughout the Universe*, *Work Made for Hire*, *Master Sound Recording*, *Controlled Composition*, *75% Minimum Statutory Mechanical Rate*, *10-Track Cap*, *Synchronization License*, *Coupling Rights*, *Moral Rights (Paternity and Integrity under Section 32 of the Copyright Act, Cap. 130)*, *Re-Recording Restriction (Holdback)*, *Digital Twin / AI Voice Synthesis*, *Power of Attorney Coupled with an Interest*.
- **Kenyan Ecosystem Specifics:** *Kenya Copyright Act (Cap. 130)*, *Kenya Copyright Board (KECOBO)*, *Collective Management Organizations (MCSK, KAMP, PRISK, PAVRISK)*, *Safaricom Skiza Tunes / Airtel Hello Tunes (CRBT)*, *KRA Withholding Tax (Income Tax Act, Cap. 470)*, *Nairobi Centre for International Arbitration (NCIA)*.

