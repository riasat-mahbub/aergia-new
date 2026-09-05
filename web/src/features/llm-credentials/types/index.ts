export type LLMProviderKey = "openai" | "anthropic" | "gemini" | "groq";

export interface LLMKeyMap {
  openai?: string;
  anthropic?: string;
  gemini?: string;
  groq?: string;
}
