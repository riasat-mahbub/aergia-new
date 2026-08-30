import client from "./client";

export type AccountTier = "free" | "premium";

export interface SessionResponse {
  authenticated: boolean;
  account_tier: AccountTier | null;
}

export interface RegistrationConfig {
  turnstile_site_key: string | null;
  turnstile_required: boolean;
  turnstile_action: string;
}

export async function getRegistrationConfig(): Promise<RegistrationConfig> {
  const { data } = await client.get<RegistrationConfig>("/auth/registration-config");
  return data;
}
