import { Document, Image as PdfImage, Page, StyleSheet, Text, View } from "@react-pdf/renderer";
import React from "react";

import type { ReportData } from "./download";

const s = StyleSheet.create({
  page: { paddingVertical: 44, paddingHorizontal: 48, fontFamily: "Times-Roman", fontSize: 10.5, lineHeight: 1.45, color: "#000" },
  logo: { alignSelf: "center", height: 30, marginBottom: 12 },
  title: { fontFamily: "Times-Bold", fontSize: 18, textAlign: "center", letterSpacing: 0.6 },
  subtitle: { fontFamily: "Times-Italic", textAlign: "center", marginTop: 3, marginBottom: 10 },
  meta: { flexDirection: "row", flexWrap: "wrap", borderTop: "1pt solid #000", borderBottom: "1pt solid #000", paddingVertical: 6 },
  metaItem: { width: "50%", fontSize: 9.5, paddingVertical: 1 },
  bold: { fontFamily: "Times-Bold" },
  notice: { border: "1pt solid #000", padding: 7, marginVertical: 10, fontSize: 9.5 },
  h2: { fontFamily: "Times-Bold", fontSize: 12.5, borderBottom: "1pt solid #000", paddingBottom: 2, marginTop: 14, marginBottom: 6 },
  h3: { fontFamily: "Times-Bold", fontSize: 11, marginTop: 9, marginBottom: 2 },
  text: { marginBottom: 4 },
  small: { fontSize: 9, color: "#333" },
  table: { borderTop: "1pt solid #000", borderLeft: "1pt solid #000", marginVertical: 4 },
  row: { flexDirection: "row" },
  th: { fontFamily: "Times-Bold", backgroundColor: "#eee", borderRight: "1pt solid #000", borderBottom: "1pt solid #000", padding: 4 },
  td: { borderRight: "1pt solid #000", borderBottom: "1pt solid #000", padding: 4 },
  block: { marginBottom: 3 },
  quote: { fontFamily: "Times-Italic", marginLeft: 10, marginTop: 1, marginBottom: 3 },
  footer: { position: "absolute", bottom: 22, width: 240, fontSize: 8, lineHeight: 1, color: "#555" },
});

const Labelled = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <Text style={s.block}>
    <Text style={s.bold}>{label}: </Text>
    {children}
  </Text>
);

/** Section numbers, skipping sections the report leaves out. */
function sectionNumbers(data: ReportData) {
  const present = {
    legend: true,
    summary: true,
    clashes: data.clashes.length > 0,
    clauses: data.clauses.length > 0,
    missing: data.missing.length > 0,
    checklist: data.checklist.length > 0,
  };
  let count = 0;
  const numbers = {} as Record<keyof typeof present, number>;
  for (const key of Object.keys(present) as (keyof typeof present)[]) {
    if (present[key]) numbers[key] = ++count;
  }
  return numbers;
}

/** Today's printable report, as a real PDF, with the Mbiu logo at the top. */
export function ReportDocument({ data, logo }: { data: ReportData; logo?: string | null }) {
  const n = sectionNumbers(data);
  return (
    <Document title={`Mbiu contract report ${data.date}`} author="Mbiu" creator="Mbiu">
      <Page size="A4" style={s.page} wrap>
        {logo && <PdfImage src={logo} style={s.logo} />}
        <Text style={s.title}>MBIU CONTRACT EVALUATION REPORT</Text>
        <Text style={s.subtitle}>Independent Objective Comparison with Standard Contract Templates</Text>
        <View style={s.meta}>
          <Text style={s.metaItem}><Text style={s.bold}>Evaluation Date: </Text>{data.date}</Text>
          <Text style={s.metaItem}><Text style={s.bold}>Contract Scope: </Text>{data.scope}</Text>
          <Text style={s.metaItem}><Text style={s.bold}>Analysis Status: </Text>{data.status}</Text>
          <Text style={s.metaItem}><Text style={s.bold}>Report ID: </Text>{data.reportId}</Text>
        </View>
        <View style={s.notice}>
          <Text>
            <Text style={s.bold}>IMPORTANT NOTICE: </Text>
            This report explains what the contract says compared with reviewed reference material. It does not judge
            whether any clause is lawful or enforceable, and it is not legal advice.
          </Text>
        </View>

        <Text style={s.h2}>{n.legend}. How to Read This Report</Text>
        <View style={s.table}>
          <View style={s.row}>
            <Text style={[s.th, { width: "28%" }]}>Label</Text>
            <Text style={[s.th, { width: "72%" }]}>Meaning for the Artist</Text>
          </View>
          {data.legend.map((l) => (
            <View key={l.label} style={s.row}>
              <Text style={[s.td, s.bold, { width: "28%" }]}>{l.label}</Text>
              <Text style={[s.td, { width: "72%" }]}>{l.meaning}</Text>
            </View>
          ))}
        </View>

        <Text style={s.h2}>{n.summary}. Summary</Text>
        <View style={s.table}>
          <View style={s.row}>
            {data.counts.map((c) => (
              <Text key={c.label} style={[s.th, { width: "25%", textAlign: "center" }]}>{c.label}</Text>
            ))}
          </View>
          <View style={s.row}>
            {data.counts.map((c) => (
              <Text key={c.label} style={[s.td, { width: "25%", textAlign: "center", fontSize: 14 }]}>{c.count}</Text>
            ))}
          </View>
        </View>
        <Text style={s.text}><Text style={s.bold}>Clauses that clash: </Text>{data.clashCount}</Text>
        <Text style={s.text}><Text style={s.bold}>Missing from your contract: </Text>{data.missingCount}</Text>
        {data.questions.length > 0 && (
          <View>
            <Text style={s.h3}>Questions to ask before you sign</Text>
            {data.questions.map((q, i) => (
              <Text key={q.question} style={s.block}>
                {i + 1}. {q.question}
                {q.where ? <Text style={s.small}> ({q.where})</Text> : null}
              </Text>
            ))}
          </View>
        )}

        {data.clashes.length > 0 && (
          <View>
            <Text style={s.h2}>{n.clashes}. Clauses that clash</Text>
            <Text style={[s.text, s.small]}>
              Mbiu shows where one clause claims to override another. It never decides which a court would apply.
            </Text>
            {data.clashes.map((c, i) => (
              <View key={i} style={{ marginBottom: 6 }}>
                <Text style={s.block}><Text style={s.bold}>{i + 1}. {c.kind}: </Text>{c.explanation}</Text>
                <Text style={s.small}>{c.where}</Text>
                <Text style={s.quote}>{c.quotes[0]}</Text>
                <Text style={s.quote}>{c.quotes[1]}</Text>
              </View>
            ))}
          </View>
        )}

        {data.clauses.length > 0 && (
          <View>
            <Text style={s.h2}>{n.clauses}. Clause by clause</Text>
            {data.clauses.map((c, i) => (
              <View key={`${c.title}-${i}`} style={{ marginBottom: 8 }}>
                <Text style={s.h3} minPresenceAhead={80}>
                  {n.clauses}.{i + 1} {c.title} — {c.label}
                </Text>
                <Text style={[s.small, s.block]}>Page {c.pages}</Text>
                <Text style={[s.block, s.bold]}>{c.headline}</Text>
                <Labelled label="In simple words">{c.inSimpleWords}</Labelled>
                <Labelled label="Why it matters">{c.whyItMatters}</Labelled>
                {c.usual && <Labelled label="What usual contracts say">{c.usual}</Labelled>}
                {c.ask && <Labelled label="Ask them this">{c.ask}</Labelled>}
                {c.sources && <Text style={[s.small, s.block]}>Compared with: {c.sources}</Text>}
                <Text style={s.small}>The exact words:</Text>
                <Text style={s.quote}>{c.exactWords}</Text>
              </View>
            ))}
          </View>
        )}

        {data.missing.length > 0 && (
          <View>
            <Text style={s.h2}>{n.missing}. Missing from your contract</Text>
            <Text style={[s.text, s.small]}>Usual contracts protect you here. Yours says nothing about it.</Text>
            {data.missing.map((m, i) => (
              <Text key={m.title} style={s.block}>
                <Text style={s.bold}>{n.missing}.{i + 1} {m.title}: </Text>
                {m.ask}
              </Text>
            ))}
          </View>
        )}

        {data.checklist.length > 0 && (
          <View>
            <Text style={s.h2}>{n.checklist}. Questions to ask: checklist</Text>
            <Text style={[s.text, s.small]}>
              Use this list with your manager, label, brand partner or lawyer. Tick each one once discussed.
            </Text>
            {data.checklist.map((q, i) => (
              <Text key={q} style={s.block}>
                [  ] {i + 1}. {q}
              </Text>
            ))}
          </View>
        )}

        <Text style={[s.small, { marginTop: 14 }]}>{data.smallPrint}</Text>
        <Text style={[s.footer, { left: 48 }]} fixed>
          Mbiu contract report · Not legal advice
        </Text>
      </Page>
    </Document>
  );
}
