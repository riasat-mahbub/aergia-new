import "@testing-library/jest-dom";

// localStorage shim (existing)
const localStorageMap = new Map<string, string>();
Object.defineProperty(globalThis, "localStorage", {
  value: {
    getItem: (key: string) => localStorageMap.get(key) ?? null,
    setItem: (key: string, value: string) => localStorageMap.set(key, value),
    removeItem: (key: string) => localStorageMap.delete(key),
    clear: () => localStorageMap.clear(),
    get length() { return localStorageMap.size; },
    key: (index: number) => [...localStorageMap.keys()][index] ?? null,
  },
  configurable: true,
});

// sessionStorage shim — added by the LLM parser feature so the keys
// module can persist keys in browser tab-scope storage. Tests stub the
// same backend the production code uses.
const sessionStorageMap = new Map<string, string>();
Object.defineProperty(globalThis, "sessionStorage", {
  value: {
    getItem: (key: string) => sessionStorageMap.get(key) ?? null,
    setItem: (key: string, value: string) => sessionStorageMap.set(key, value),
    removeItem: (key: string) => sessionStorageMap.delete(key),
    clear: () => sessionStorageMap.clear(),
    get length() { return sessionStorageMap.size; },
    key: (index: number) => [...sessionStorageMap.keys()][index] ?? null,
  },
  configurable: true,
});
