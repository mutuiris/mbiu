// pdf.js 6 uses JavaScript that Safari and older Chrome lack. Without these the contract
// viewer throws and the whole page shows "This page couldn't load".

// Map/WeakMap getOrInsert and getOrInsertComputed
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

// `for await (const chunk of readableStream)`, which Safari does not support
type IterableStream = {
  [Symbol.asyncIterator]?: (this: ReadableStream) => AsyncGenerator<unknown>;
  values?: (this: ReadableStream) => AsyncGenerator<unknown>;
};

if (typeof ReadableStream !== "undefined") {
  const proto = ReadableStream.prototype as unknown as IterableStream;
  proto[Symbol.asyncIterator] ??= async function* (this: ReadableStream) {
    const reader = this.getReader();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) return;
        yield value;
      }
    } finally {
      reader.releaseLock();
    }
  };
  proto.values ??= proto[Symbol.asyncIterator];
}

export {};
