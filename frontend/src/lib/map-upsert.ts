// pdf.js 6 calls Map/WeakMap getOrInsert and getOrInsertComputed, which Safari and
// older Chrome lack; without them the contract viewer crashes the whole page.
type Upsert = {
  has(key: unknown): boolean;
  get(key: unknown): unknown;
  set(key: unknown, value: unknown): unknown;
  getOrInsert?: (key: unknown, value: unknown) => unknown;
  getOrInsertComputed?: (key: unknown, compute: (key: unknown) => unknown) => unknown;
};

for (const proto of [Map.prototype, WeakMap.prototype] as unknown as Upsert[]) {
  proto.getOrInsert ??= function (this: Upsert, key, value) {
    if (!this.has(key)) this.set(key, value);
    return this.get(key);
  };
  proto.getOrInsertComputed ??= function (this: Upsert, key, compute) {
    if (!this.has(key)) this.set(key, compute(key));
    return this.get(key);
  };
}

export {};
