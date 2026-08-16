const HTTP_SCHEMES = new Set(["http:", "https:"]);
const LINK_SCHEMES = new Set(["http:", "https:", "mailto:", "tel:"]);

function hasUnsafeCharacters(value: string): boolean {
  return [...value].some((character) => {
    const code = character.charCodeAt(0);
    return code < 0x20 || code === 0x7f || /\s/.test(character);
  });
}

/** Normalize an allowlisted URL for use in an external anchor. */
export function safeExternalUrl(value: string | null | undefined): string | null {
  return safeUrl(value, HTTP_SCHEMES);
}

/** Normalize a rich-text/contact URL, including mailto: and tel:. */
export function safeLinkUrl(value: string | null | undefined): string | null {
  return safeUrl(value, LINK_SCHEMES);
}

function safeUrl(value: string | null | undefined, allowed: Set<string>): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim();
  if (!text || hasUnsafeCharacters(text) || text.startsWith("//")) return null;

  const schemeMatch = text.match(/^[a-z][a-z\d+.-]*:/i);
  const hasScheme = schemeMatch !== null;
  const candidate = hasScheme ? text : `https://${text}`;
  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch {
    return null;
  }

  const protocol = parsed.protocol.toLowerCase();
  if (!allowed.has(protocol)) return null;
  if (HTTP_SCHEMES.has(protocol)) {
    if (!parsed.hostname || parsed.username || parsed.password || text.includes("\\")) return null;
  } else if (!parsed.pathname || parsed.hostname) {
    // mailto:/tel: are opaque contact URLs, not host-bearing URLs.
    return null;
  }
  // Keep the stable textual form used by the API (including an explicit
  // URL's path spelling) while canonicalizing the scheme and adding HTTPS
  // to bare hosts.
  return hasScheme
    ? `${protocol}${text.slice(schemeMatch[0].length)}`
    : `https://${text}`;
}
