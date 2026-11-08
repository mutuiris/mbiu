import { describe, expect, it } from "vitest";

describe("browser-polyfills", () => {
  it("adds Map upserts and stream iteration where the browser lacks them", async () => {
    for (const proto of [Map.prototype, WeakMap.prototype] as object[]) {
      delete (proto as Record<string, unknown>).getOrInsert;
      delete (proto as Record<string, unknown>).getOrInsertComputed;
    }
    const streamProto = ReadableStream.prototype as unknown as Record<PropertyKey, unknown>;
    delete streamProto[Symbol.asyncIterator];
    delete streamProto.values;
    await import("./browser-polyfills");

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

    const stream = new ReadableStream<number>({
      start(controller) {
        controller.enqueue(1);
        controller.enqueue(2);
        controller.close();
      },
    });
    const seen: number[] = [];
    for await (const value of stream as unknown as AsyncIterable<number>) seen.push(value);
    expect(seen).toEqual([1, 2]);
  });
});
