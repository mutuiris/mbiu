import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { ClauseResult } from "@/lib/api/generated/types.gen";
import type { GroupedResults } from "@/lib/report";

import { ClauseSection } from "./ClauseSection";

const r = (clause_id: string, comparison: ClauseResult["comparison"]) =>
  ({ clause_id, comparison }) as ClauseResult;

const grouped: GroupedResults = {
  cards: [r("a", "not_in_standard"), r("b", "not_in_standard")],
  standard: [],
  cannotCompare: [r("c", "cannot_compare")],
  writeUps: [],
  counts: { typical: 0, unusual: 2, worth_asking_about: 0, cannot_compare: 1 },
};
const render = (props: Partial<React.ComponentProps<typeof ClauseSection>> = {}) =>
  renderToStaticMarkup(
    <ClauseSection
      grouped={grouped}
      renderCard={(res) => <p key={res.clause_id}>card {res.clause_id}</p>}
      failedCards={[]}
      notCheckedNames={["Clause 9 · Notices", "Clause 10"]}
      onCheckRest={() => {}}
      {...props}
    />,
  );

describe("ClauseSection", () => {
  it("shows only filters that have clauses, with counts", () => {
    const html = render();
    expect(html).toContain("All checked · 3");
    expect(html).toContain("Unusual · 2");
    expect(html).toContain("Couldn&#x27;t compare · 1");
    expect(html).not.toContain("Worth inquiry ·");
    expect(html).not.toContain("Typical ·");
  });

  it("shows finding cards and folds the rest into rows", () => {
    const html = render();
    expect(html).toContain("card a");
    expect(html).toContain("1 clause with no usual contract to compare");
    expect(html).toContain("2 clauses not checked yet");
    expect(html).toContain("Check them");
    expect(html).not.toContain("standard and boilerplate");
  });

  it("opens the fold that holds the clause the artist jumped to", () => {
    const withStandard: GroupedResults = { ...grouped, standard: [r("s1", "matches_standard")], counts: { ...grouped.counts, typical: 1 } };
    expect(render({ grouped: withStandard })).not.toContain("data-panel-open");
    expect(render({ grouped: withStandard, selectedClauseId: "s1" })).toContain("data-panel-open");
    expect(render({ selectedClauseId: "c" })).toContain("data-panel-open");
  });

  it("renders nothing when there is nothing to show", () => {
    expect(
      render({
        grouped: { cards: [], standard: [], cannotCompare: [], writeUps: [], counts: { typical: 0, unusual: 0, worth_asking_about: 0, cannot_compare: 0 } },
        notCheckedNames: [],
      }),
    ).toBe("");
  });
});
