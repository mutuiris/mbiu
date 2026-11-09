"""Generate a synthetic 40-page music agreement PDF at the exact upload page cap.

Uses PyMuPDF to generate a valid, text-based PDF in memory and save it to the
fixtures directory. Strictly synthetic content—never contains real contract text.
"""

from __future__ import annotations

from pathlib import Path
import pymupdf

OUTPUT_DIR = Path(__file__).resolve().parent / "fixtures"
OUTPUT_FILE = OUTPUT_DIR / "contract_40p.pdf"

PAGE_WIDTH = 595.0   # A4 width in points
PAGE_HEIGHT = 842.0  # A4 height in points
MARGIN_X = 54.0
MARGIN_TOP = 64.0
LINE_HEIGHT = 15.0

# 40 distinct sections / pages representing a complete 40-page recording agreement
PAGE_SECTIONS: list[tuple[str, str]] = [
    (
        "Page 1: Title and Parties Recitals",
        "THIS EXCLUSIVE ARTIST RECORDING AGREEMENT is made and entered into as of January 15, 2026, "
        "by and between SOUNDCRAFT ENTERTAINMENT LIMITED, a company incorporated in the Republic of Kenya "
        "(hereinafter referred to as the 'Company' or 'Label'), and THE ARTIST professionally known as "
        "'SAUTI YA JUA' (hereinafter referred to as the 'Artist').\n\n"
        "WHEREAS the Company carries on business as a record label, sound recording producer, and distributor; "
        "and WHEREAS the Artist is an author, performer, and recording musician desiring to grant exclusive "
        "recording and exploitation rights to the Company subject to the terms and conditions herein contained."
    ),
    (
        "Page 2: Clause 1 — Definitions and Interpretations",
        "1.1 In this Agreement, unless the context otherwise requires:\n"
        "(a) 'Commercial Release' means the initial public distribution or streaming availability of a Master;\n"
        "(b) 'Contract Period' means the Initial Period together with any Option Periods exercised by the Company;\n"
        "(c) 'Gross Receipts' means all monies actually received by Company from digital streaming, physical sales, "
        "and synchronization licensing directly identifiable to the Masters hereunder;\n"
        "(d) 'Masters' means all sound recordings and underlying musical performances recorded by Artist during the Term."
    ),
    (
        "Page 3: Clause 2 — Territory and Geographic Scope",
        "2.1 Territory. The rights granted under this Agreement shall apply throughout the Universe.\n\n"
        "2.2 Digital Exploitation. Worldwide digital distribution across all digital service providers (DSPs), "
        "telecommunication value-added services (CRBT / Skiza Tunes), and interactive streaming networks shall "
        "be administered exclusively by the Company without territorial limitation."
    ),
    (
        "Page 4: Clause 3 — Initial Term and Option Periods",
        "3.1 Initial Period. The initial period of this Agreement shall commence on the Effective Date and shall "
        "continue for twelve (12) consecutive months from the date of initial commercial delivery of the first Album.\n\n"
        "3.2 Option Periods. The Artist hereby grants to Company four (4) separate, consecutive options to extend "
        "the Term for additional periods of twelve (12) months each, exercisable by Company in writing at least "
        "thirty (30) days prior to the expiration of the then-current period."
    ),
    (
        "Page 5: Clause 4 — Recording Commitment and Delivery",
        "4.1 Minimum Commitment. During each Contract Period, Artist shall record and deliver to Company a minimum "
        "of ten (10) technically and commercially satisfactory Masters comprising one (1) full-length Album.\n\n"
        "4.2 Approval of Material. Selection of compositions, producers, studios, and guest vocalists shall require "
        "the mutual consent of Artist and Company, provided that Company's reasonable commercial decision shall govern."
    ),
    (
        "Page 6: Clause 5 — Grant of Rights and Master Ownership",
        "5.1 Assignment of Masters. Artist hereby assigns and transfers to Company all worldwide rights, title, "
        "and interest (including copyright) in and to all sound recordings created during the Term, for the full "
        "statutory duration of copyright and all renewals and extensions thereof.\n\n"
        "5.2 Standard Comparison Note: Standard Kenyan music industry guidelines recommend licensing masters for a "
        "limited term of 5 to 7 years rather than permanent assignments in perpetuity."
    ),
    (
        "Page 7: Clause 6 — Artist Advances and Living Stipends",
        "6.1 Production Advance. Company shall pay Artist a non-refundable, recoupable advance of KES 500,000 "
        "upon execution of this Agreement, and KES 300,000 upon satisfactory commercial delivery of each Album.\n\n"
        "6.2 Living Allowance. Company may, at its sole discretion, advance living and maintenance allowances to "
        "Artist subject to full recoupment from royalties accrued under Clause 8."
    ),
    (
        "Page 8: Clause 7 — Recoupment Mechanics and Limits",
        "7.1 Recoupable Costs. Direct recording costs, mastering costs, video production budgets approved by Artist, "
        "and direct tour support shall be recoupable solely from Artist's royalties.\n\n"
        "7.2 General Overhead. In no event shall Company recoup its general administrative overhead, rent, legal fees "
        "incurred in negotiating this Agreement, or standard staff salaries from Artist's royalties."
    ),
    (
        "Page 9: Clause 8 — Royalty Rates and Shillings Calculation",
        "8.1 Streaming Royalty. Company shall pay Artist a royalty of 16% of Net Receipts derived from digital "
        "streaming and digital downloads.\n\n"
        "8.2 Physical Sales. For physical CD and vinyl sales in East Africa, Company shall pay a royalty of 12% "
        "of the Recommended Retail Price (RRP) less standard packaging deductions of not more than 10%."
    ),
    (
        "Page 10: Clause 9 — Skiza and Caller Ring Back Tunes (CRBT)",
        "9.1 Telecommunication Royalties. For all revenue received from Skiza Tunes and local telecom ringback services, "
        "Company shall pay Artist seventy percent (70%) of the net distributor payouts received from Safaricom/Prism.\n\n"
        "9.2 Payment Timelines. Skiza payments shall be disbursed within thirty (30) days of receipt by Company."
    ),
    (
        "Page 11: Clause 10 — Accounting Statements and Payment Frequency",
        "10.1 Semi-Annual Accounting. Company shall compute royalties within sixty (60) days following June 30 and "
        "December 31 of each calendar year, and furnish Artist with a detailed statement accompanied by payment.\n\n"
        "10.2 Transparent Breakdowns. Statements shall enumerate streaming volumes per platform, gross collections, "
        "and specific line-item recoupment deductions."
    ),
    (
        "Page 12: Clause 11 — Audit and Books Inspection Rights",
        "11.1 Annual Audit. Artist may, upon thirty (30) days' written notice, engage an independent certified public "
        "accountant to inspect Company's books and records relating to sales and revenue under this Agreement.\n\n"
        "11.2 Audit Discrepancy. If an audit reveals an underpayment exceeding ten percent (10%) and not less than "
        "KES 50,000, Company shall promptly pay the deficiency together with reasonable audit fees."
    ),
    (
        "Page 13: Clause 12 — Exclusivity and Side-Artist Work",
        "13.1 Exclusivity. During the Term, Artist shall perform and record exclusively for Company and shall not "
        "render recording services for any third party without Company's prior written approval.\n\n"
        "13.2 Guest Collaborations. Artist may participate as an uncredited or featured guest vocalist on third-party "
        "recordings provided such release does not compete directly with Artist's current single."
    ),
    (
        "Page 14: Clause 13 — Live Performances and Gig Earnings",
        "14.1 Live Freedom. Artist retains the unrestricted right to book and perform live concerts, festivals, "
        "club gigs, and public appearances, and shall retain one hundred percent (100%) of all live performance fees.\n\n"
        "14.2 Non-Interference. Live scheduling shall not conflict with confirmed promotional tours or recording sessions."
    ),
    (
        "Page 15: Clause 14 — Name, Image, Likeness (NIL) and Publicity",
        "15.1 Promotional Grant. Artist grants Company the non-exclusive right during the Term to use Artist's "
        "approved name, biography, likeness, and photographs solely in connection with marketing the Masters.\n\n"
        "15.2 Commercial Endorsements. Commercial brand sponsorships and personal product endorsements remain "
        "the exclusive property of Artist and require separate mutual agreement."
    ),
    (
        "Page 16: Clause 15 — Merchandising and Tour Goods",
        "16.1 Merchandising Option. If Artist elects to grant Company merchandising rights, Company shall pay "
        "Artist fifty percent (50%) of Net Merchandising Profits from tour goods and apparel.\n\n"
        "16.2 Quality Control. All artwork and branded garments must receive Artist's written approval prior to sale."
    ),
    (
        "Page 17: Clause 16 — Music Video Production and Visual Rights",
        "17.1 Video Budgets. Company shall produce at least two (2) music videos per Album with an agreed minimum "
        "production budget of KES 400,000 per video.\n\n"
        "17.2 Video Recoupment. Video production expenses shall be fifty percent (50%) recoupable from Artist's "
        "audio royalties and one hundred percent (100%) recoupable from video streaming revenues."
    ),
    (
        "Page 18: Clause 17 — Moral Rights and Credit Protection",
        "18.1 Paternity Credit. Company agrees that Artist shall receive prominent credit on all commercial releases, "
        "liner notes, streaming metadata, and promotional materials as the principal performer.\n\n"
        "18.2 Integrity of Work. No Master delivered by Artist shall be materially altered, remixed, or sampled "
        "without Artist's prior consultation and written consent."
    ),
    (
        "Page 19: Clause 18 — Publishing and Songwriting Separation",
        "19.1 Publishing Excluded. This Agreement is strictly a recording agreement. Company acquires no copyright, "
        "co-publishing share, or administration rights in the underlying musical compositions written by Artist.\n\n"
        "19.2 Mechanical Royalties. Company shall pay statutory mechanical royalties for all Artist-written compositions "
        "embodied on physical and digital releases at 100% of standard KECOBO rates."
    ),
    (
        "Page 20: Clause 19 — Producer Engagements and Points",
        "20.1 Producer Agreements. Company shall engage and contract all music producers subject to Artist's approval.\n\n"
        "20.2 Producer Royalties. Producer royalties (typically 3% to 4%) shall be deducted from Artist's gross "
        "all-in royalty rate only after full recoupment of the applicable recording costs."
    ),
    (
        "Page 21: Clause 20 — Warranties and Representations",
        "21.1 Artist Warranties. Artist warrants and represents that Artist has the legal capacity to enter into this "
        "Agreement and that Masters delivered do not infringe upon any third-party copyright or trademark.\n\n"
        "21.2 Company Warranties. Company warrants that it is duly licensed and possesses the financial and distribution "
        "capacity to perform all commitments hereunder."
    ),
    (
        "Page 22: Clause 21 — Indemnification and Defense",
        "22.1 Mutual Indemnity. Each party agrees to indemnify and hold harmless the other party against any direct "
        "damages or legal expenses arising from a final adjudicated breach of the express warranties in Clause 20.\n\n"
        "22.2 Settlement Approval. No claim shall be settled without the indemnifying party's prior written consent."
    ),
    (
        "Page 23: Clause 22 — Breach, Cure Notice, and Remedies",
        "23.1 Notice of Default. Prior to terminating this Agreement for breach, the aggrieved party must serve written "
        "notice specifying the nature of the alleged failure.\n\n"
        "23.2 Thirty-Day Cure. The defaulting party shall have thirty (30) business days from receipt of notice to cure "
        "such default before any right of legal action or termination arises."
    ),
    (
        "Page 24: Clause 23 — Reversion of Rights upon Inactivity",
        "24.1 Reversion Trigger. If Company fails to commercially release a delivered Album within nine (9) months of "
        "technical delivery, all rights in such unreleased Masters shall automatically revert to Artist free and clear.\n\n"
        "24.2 Unrecouped Costs Waiver. Upon reversion under this Clause, Artist shall have no obligation to reimburse "
        "any recording advances incurred in connection with the unreleased Masters."
    ),
    (
        "Page 25: Clause 24 — Re-Recording Restrictions",
        "25.1 Restriction Period. Artist agrees not to re-record any composition embodied in a released Master for "
        "any third party for a period of three (3) years following the expiration of the Term.\n\n"
        "25.2 Live Exceptions. This restriction shall not prohibit Artist from performing such songs in live concerts "
        "or acoustic non-commercial radio sessions."
    ),
    (
        "Page 26: Clause 25 — Controlled Compositions and Reductions",
        "26.1 Controlled Compositions. Mechanical royalties for musical works written by Artist shall not be subject "
        "to a three-quarter (75%) reduction, but shall be paid at one hundred percent (100%) of statutory tariff.\n\n"
        "26.2 Maximum Cap. Company shall not apply a maximum cap of fewer than 12 tracks per Album."
    ),
    (
        "Page 27: Clause 26 — Key-Person Clause and Staff Stability",
        "27.1 Key Executive. This Agreement is entered into in reliance upon the personal creative direction of "
        "Executive Producer John Mutua ('Key Person').\n\n"
        "27.2 Termination Option. If the Key Person ceases to be actively employed by Company, Artist shall have the "
        "option to terminate the remainder of the Term upon sixty (60) days' notice."
    ),
    (
        "Page 28: Clause 27 — Health, Insurance, and Travel Welfare",
        "28.1 Travel Safety. When Company requires Artist to travel internationally for promotion, Company shall "
        "provide round-trip airfare, standard hotel accommodations, and comprehensive emergency travel health insurance.\n\n"
        "28.2 Per Diem Allowance. Company shall provide an agreed daily subsistence stipend during official travel."
    ),
    (
        "Page 29: Clause 28 — Force Majeure and Suspensions",
        "29.1 Excusable Delay. Neither party shall be liable for delays in recording or release caused by acts of God, "
        "epidemics, civil unrest, or statutory government bans on public gatherings.\n\n"
        "29.2 Duration Cap. If a force majeure event continues for longer than six (6) consecutive months, either "
        "party may terminate this Agreement without penalty."
    ),
    (
        "Page 30: Clause 29 — Independent Legal Advice Certification",
        "30.1 Opportunity for Counsel. Artist acknowledges that Company advised Artist to seek independent legal "
        "representation prior to signing this Agreement.\n\n"
        "30.2 Voluntary Execution. Artist confirms that Artist has read and understood all clauses contained herein "
        "and executes this document freely and voluntarily."
    ),
    (
        "Page 31: Clause 30 — Confidentiality and Non-Disclosure",
        "31.1 Proprietary Terms. The financial provisions and royalty percentages of this Agreement are confidential "
        "and shall not be disclosed to any third party except legal and financial advisors.\n\n"
        "31.2 Permitted Disclosures. Disclosure required by statutory law, court subpoena, or tax authorities is permitted."
    ),
    (
        "Page 32: Clause 31 — Cross-Collateralization Prohibition",
        "32.1 Separate Accounting. Advances and costs incurred under this Agreement shall not be cross-collateralized "
        "against earnings from any publishing, live booking, or merchandising agreements between the parties.\n\n"
        "32.2 No Cross-Deduction. Each Album's account shall stand independently for recoupment purposes."
    ),
    (
        "Page 33: Clause 32 — Notices and Communications",
        "33.1 Formal Notice. Any notice required under this Agreement shall be in writing and delivered by registered "
        "post or electronic mail to the designated addresses set forth in Schedule A.\n\n"
        "33.2 Deemed Receipt. Electronic notices shall be deemed received twenty-four (24) hours after transmission."
    ),
    (
        "Page 34: Clause 33 — Governing Law and Jurisdiction",
        "34.1 Laws of Kenya. This Agreement shall be governed by and construed in accordance with the laws of Kenya.\n\n"
        "34.2 Court Jurisdiction. The parties submit to the exclusive jurisdiction of the High Court of Kenya "
        "sitting at Nairobi for the resolution of any dispute arising hereunder."
    ),
    (
        "Page 35: Clause 34 — Alternative Dispute Resolution (ADR)",
        "35.1 Mediation First. Before instituting court proceedings, the parties agree to submit any unresolved "
        "dispute to mediation under the auspices of the Strathmore Dispute Resolution Centre (SDRC).\n\n"
        "35.2 Arbitral Referral. If mediation fails within forty-five (45) days, the matter shall be referred to "
        "arbitration in accordance with the Kenyan Arbitration Act (Cap. 49)."
    ),
    (
        "Page 36: Clause 35 — Entire Agreement and Amendments",
        "36.1 Full Understanding. This Agreement, including Schedules A through E, constitutes the entire understanding "
        "between the parties and supersedes all prior verbal or written understandings.\n\n"
        "36.2 Written Variation. No amendment or modification shall be valid unless executed in writing by both parties."
    ),
    (
        "Page 37: Schedule A — Contact Addresses and Banking Details",
        "SCHEDULE A: NOTICES AND DISBURSEMENTS\n\n"
        "1. Company Notice Address: Soundcraft Entertainment Ltd, P.O. Box 45200-00100, Nairobi, Kenya.\n"
        "   Email: legal@soundcraftke.example\n\n"
        "2. Artist Notice Address: P.O. Box 12890-00200, Nairobi, Kenya.\n"
        "   Email: sautiyajua@artistke.example\n\n"
        "3. Designated Bank Account: Equity Bank Kenya, Commercial Account No. 0180293847291."
    ),
    (
        "Page 38: Schedule B — Approved Recording Studios and Engineers",
        "SCHEDULE B: PRODUCTION SPECIFICATIONS\n\n"
        "1. Approved Primary Studios: AudioCraft Studios Nairobi, Sub-Sahara Sound Labs Karen.\n"
        "2. Delivery Standards: 24-bit / 96kHz uncompressed WAV files along with full instrument stems, "
        "vocal tracks, and MIDI arrangements.\n"
        "3. Metadata Sheets: Complete ISRC codes, songwriter splits, and producer credits must accompany masters."
    ),
    (
        "Page 39: Schedule C — Approved Territory and Digital Outlets",
        "SCHEDULE C: DIGITAL SERVICE PROVIDERS AND DSP LISTING\n\n"
        "Authorized DSPs include but are not limited to: Spotify, Apple Music, Boomplay Music Kenya, YouTube Music, "
        "Audiomack, Mdundo, Tidal, Deezer, and Amazon Music. Ringback and telecommunication distribution "
        "licensed through Safaricom PLC, Airtel Kenya, and Telkom Kenya."
    ),
    (
        "Page 40: Schedule D & E — Execution Signatures and Attestation",
        "IN WITNESS WHEREOF, the parties hereto have executed this Exclusive Artist Recording Agreement "
        "as of the day and year first above written.\n\n"
        "SIGNED for and on behalf of SOUNDCRAFT ENTERTAINMENT LIMITED:\n"
        "Signature: ___________________________\n"
        "Name: David Mwangi, Managing Director\n\n"
        "SIGNED by THE ARTIST (SAUTI YA JUA):\n"
        "Signature: ___________________________\n"
        "Name: Mercyline Nyaboke, Artist\n\n"
        "WITNESSED BY (Advocate of the High Court of Kenya):\n"
        "Signature: ___________________________\n"
        "Name: Commissioner for Oaths, Nairobi"
    ),
]


def generate_40_page_contract() -> Path:
    """Generate the synthetic 40-page contract PDF and save to disk."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()

    for idx, (heading, body) in enumerate(PAGE_SECTIONS, start=1):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        # Header / Title
        page.insert_text(
            (MARGIN_X, MARGIN_TOP),
            heading,
            fontsize=12.0,
            fontname="helv",
            color=(0.1, 0.1, 0.3),
        )
        # Subtitle rule
        page.draw_line(
            (MARGIN_X, MARGIN_TOP + 8),
            (PAGE_WIDTH - MARGIN_X, MARGIN_TOP + 8),
            color=(0.7, 0.7, 0.7),
            width=1,
        )
        # Body text
        rect = pymupdf.Rect(
            MARGIN_X,
            MARGIN_TOP + 24,
            PAGE_WIDTH - MARGIN_X,
            PAGE_HEIGHT - 60,
        )
        page.insert_textbox(
            rect,
            body,
            fontsize=10.0,
            fontname="helv",
            color=(0.2, 0.2, 0.2),
            lineheight=LINE_HEIGHT,
        )
        # Page footer
        page.insert_text(
            (MARGIN_X, PAGE_HEIGHT - 30),
            f"Mbiu Synthetic Load Benchmark Agreement — Page {idx} of {len(PAGE_SECTIONS)}",
            fontsize=8.0,
            fontname="helv",
            color=(0.5, 0.5, 0.5),
        )

    doc.save(str(OUTPUT_FILE))
    doc.close()
    return OUTPUT_FILE


if __name__ == "__main__":
    path = generate_40_page_contract()
    doc = pymupdf.open(str(path))
    print(f"Generated synthetic 40-page contract: {path} ({len(doc)} pages, {path.stat().st_size} bytes)")
    doc.close()
