import type { LLMKeyMap, LLMProviderKey } from "@/features/llm-credentials/types";

/** API keys are not account passwords; prevent password-manager cross-fill. */
export const PROVIDER_AUTOCOMPLETE: Record<LLMProviderKey, string> = {
  openai: "off",
  anthropic: "off",
  gemini: "off",
  groq: "off",
};

export const PROVIDER_PREFIXES: Record<LLMProviderKey, string> = {
  openai: "sk-",
  anthropic: "sk-ant-",
  gemini: "AIza",
  groq: "gsk_",
};

export const PROVIDER_LABELS: Record<LLMProviderKey, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  gemini: "Gemini",
  groq: "Groq",
};

export const PROVIDER_ORDER: readonly LLMProviderKey[] = [
  "openai",
  "anthropic",
  "gemini",
  "groq",
];

export function detectProviderShape(raw: string): LLMProviderKey | null {
  const trimmed = (raw ?? "").trim();
  if (!trimmed) return null;
  if (trimmed.startsWith(PROVIDER_PREFIXES.anthropic)) return "anthropic";
  if (trimmed.startsWith(PROVIDER_PREFIXES.openai)) return "openai";
  if (trimmed.startsWith(PROVIDER_PREFIXES.gemini)) return "gemini";
  if (trimmed.startsWith(PROVIDER_PREFIXES.groq)) return "groq";
  return null;
}

export function pickActiveProvider(map: LLMKeyMap): LLMProviderKey | null {
  for (const provider of PROVIDER_ORDER) {
    const value = map[provider];
    if (typeof value === "string" && value.trim()) return provider;
  }
  return null;
}
