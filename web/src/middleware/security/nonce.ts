const NONCE_BYTE_LENGTH = 18;

function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);

  const base64 = btoa(binary);
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

/** Generate a per-request value suitable for a CSP nonce and HTML attribute. */
export function createCspNonce(): string {
  const bytes = new Uint8Array(NONCE_BYTE_LENGTH);
  globalThis.crypto.getRandomValues(bytes);
  return bytesToBase64Url(bytes);
}
