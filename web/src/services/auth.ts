import client, { refreshSession as refreshSessionRequest } from "./client";
import type {
  AccountTier,
  LoginRequest,
  RegisterRequest,
  RegistrationConfig,
  SessionResponse,
} from "@/contracts/auth";

export async function getSession(): Promise<SessionResponse> {
  const { data } = await client.get<SessionResponse>("/auth/session");
  return data;
}

export async function refreshAuthenticatedSession(): Promise<void> {
  await refreshSessionRequest();
}

export async function getAccountTier(): Promise<AccountTier | null> {
  try {
    const session = await getSession();
    return session.account_tier === "free" || session.account_tier === "premium" ? session.account_tier : null;
  } catch {
    return null;
  }
}

export async function login(input: LoginRequest): Promise<void> {
  await client.post("/auth/login", input);
}

export async function register(input: RegisterRequest): Promise<void> {
  await client.post("/auth/register", input);
}

export async function logout(): Promise<void> {
  await client.post("/auth/logout");
}

export async function getRegistrationConfig(): Promise<RegistrationConfig> {
  const { data } = await client.get<RegistrationConfig>("/auth/registration-config");
  return data;
}
