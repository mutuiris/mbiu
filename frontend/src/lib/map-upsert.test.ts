import { describe, expect, it } from "vitest";

describe("map-upsert", () => {
  it("adds getOrInsert and getOrInsertComputed where the browser lacks them", async () => {
    for (const proto of [Map.prototype, WeakMap.prototype] as object[]) {
      delete (proto as Record<string, unknown>).getOrInsert;
      delete (proto as Record<string, unknown>).getOrInsertComputed;
    }
    await import("./map-upsert");

    type Upsert = {
      getOrInsert(key: unknown, value: unknown): unknown;
      getOrInsertComputed(key: unknown, compute: (key: unknown) => unknown): unknown;
    };
    const map = new Map<string, string[]>() as unknown as Upsert & Map<string, string[]>;
    let calls = 0;
    const list = map.getOrInsertComputed("a", () => (calls++, [])) as string[];
    list.push("x");
    expect(map.getOrInsertComputed("a", () => (calls++, []))).toEqual(["x"]);
    expect(calls).toBe(1);
    expect(map.getOrInsert("b", ["y"])).toEqual(["y"]);
    expect(map.getOrInsert("b", ["z"])).toEqual(["y"]);

    const key = {};
    const weak = new WeakMap() as unknown as Upsert;
    expect(weak.getOrInsertComputed(key, () => 1)).toBe(1);
    expect(weak.getOrInsertComputed(key, () => 2)).toBe(1);
  });
});
