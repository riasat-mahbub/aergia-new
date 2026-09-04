export type AccountTier = "free" | "premium";

export interface SessionResponse {
  authenticated: boolean;
  account_tier: AccountTier | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  turnstile_token?: string;
}

export interface RegistrationConfig {
  turnstile_site_key: string | null;
  turnstile_required: boolean;
  turnstile_action: string;
}
