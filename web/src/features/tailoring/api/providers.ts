import client from "@/shared/api/client";
import type {
  TailoringProvider,
  TailoringProviderOAuthCallbackRequest,
  TailoringProviderStatusResponse,
  TailoringProvidersResponse,
  TailoringSessionStatusResponse,
} from "../types";

export async function getTailoringProviders(): Promise<TailoringProvidersResponse> {
  const { data } = await client.get("/tailoring/providers", { errorToast: "local" });
  return data;
}

export async function connectTailoringProvider(provider: TailoringProvider): Promise<{ authorization_url: string }> {
  const { data } = await client.post(`/tailoring/providers/${provider}/connect`);
  return data;
}

export async function disconnectTailoringProvider(provider: TailoringProvider): Promise<TailoringProviderStatusResponse> {
  const { data } = await client.post(`/tailoring/providers/${provider}/disconnect`);
  return data;
}

export async function checkGeminiTailoringSetup(): Promise<TailoringProviderStatusResponse> {
  const { data } = await client.post("/tailoring/providers/gemini/check");
  return data;
}

export async function completeTailoringProviderOAuthCallback(
  request: TailoringProviderOAuthCallbackRequest,
): Promise<TailoringProviderStatusResponse> {
  const { data } = await client.post("/tailoring/providers/callback", request);
  return data;
}

export async function createProviderTailoringRun(
  applicationId: string,
  provider: TailoringProvider,
): Promise<TailoringSessionStatusResponse> {
  const { data } = await client.post(`/applications/${applicationId}/tailoring/provider-runs`, { provider });
  return data;
}
