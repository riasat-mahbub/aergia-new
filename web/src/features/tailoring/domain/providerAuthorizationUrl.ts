import { safeExternalUrl } from "@/shared/security/safeUrl";
import type { TailoringProvider } from "../types";

const AUTHORIZATION_HOSTS: Record<TailoringProvider, string> = {
  chatgpt: "auth.openai.com",
  gemini: "accounts.google.com",
};

/** Accept only the provider's HTTPS authorization endpoint before redirecting. */
export function safeProviderAuthorizationUrl(
  provider: TailoringProvider,
  value: string | null | undefined,
): string | null {
  const safeUrl = safeExternalUrl(value);
  if (!safeUrl) return null;

  try {
    const parsed = new URL(safeUrl);
    if (
      parsed.protocol !== "https:"
      || parsed.hostname.toLowerCase() !== AUTHORIZATION_HOSTS[provider]
      || parsed.username
      || parsed.password
    ) return null;
    return parsed.toString();
  } catch {
    return null;
  }
}
