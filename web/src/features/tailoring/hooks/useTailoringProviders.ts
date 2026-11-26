import { useCallback, useEffect, useRef, useState } from "react";
import {
  checkGeminiTailoringSetup,
  connectTailoringProvider,
  disconnectTailoringProvider,
  getTailoringProviders,
} from "../api/providers";
import { safeProviderAuthorizationUrl } from "../domain/providerAuthorizationUrl";
import type {
  TailoringProvider,
  TailoringProviderAccount,
  TailoringProviderAvailability,
  TailoringProviderStatusResponse,
} from "../types";

function providerAccount(response: TailoringProviderStatusResponse): TailoringProviderAccount {
  return { status: response.status, detail: response.detail };
}

function responseStatus(error: unknown): number | null {
  if (typeof error !== "object" || error === null || !("response" in error)) return null;
  const response = error.response;
  if (typeof response !== "object" || response === null || !("status" in response)) return null;
  return typeof response.status === "number" ? response.status : null;
}

export function useTailoringProviders() {
  const [availability, setAvailability] = useState<TailoringProviderAvailability>({ state: "loading" });
  const requestGenerationRef = useRef(0);

  const loadProviders = useCallback(async () => {
    try {
      const providers = await getTailoringProviders();
      return { state: "loaded", providers } as const;
    } catch (error) {
      if (responseStatus(error) === 404) {
        return { state: "unsupported" } as const;
      }
      return { state: "failed", message: "Provider status could not be loaded. Try again." } as const;
    }
  }, []);

  useEffect(() => {
    const generation = ++requestGenerationRef.current;
    void loadProviders().then((result) => {
      if (requestGenerationRef.current === generation) setAvailability(result);
    });
    return () => { requestGenerationRef.current += 1; };
  }, [loadProviders]);

  const refresh = useCallback(async () => {
    const generation = ++requestGenerationRef.current;
    setAvailability({ state: "loading" });
    const result = await loadProviders();
    if (requestGenerationRef.current === generation) setAvailability(result);
  }, [loadProviders]);

  const connect = useCallback(async (provider: TailoringProvider) => {
    const response = await connectTailoringProvider(provider);
    const authorizationUrl = safeProviderAuthorizationUrl(provider, response.authorization_url);
    if (!authorizationUrl) {
      throw new Error("The provider returned an invalid sign-in URL. Try again from Settings.");
    }
    window.location.assign(authorizationUrl);
  }, []);

  const disconnect = useCallback(async (provider: TailoringProvider) => {
    const generation = requestGenerationRef.current;
    const response = await disconnectTailoringProvider(provider);
    if (requestGenerationRef.current === generation) {
      setAvailability((current) => current.state === "loaded"
        ? { state: "loaded", providers: { ...current.providers, [provider]: providerAccount(response) } }
        : current);
    }
    return response;
  }, []);

  const checkGemini = useCallback(async () => {
    const generation = requestGenerationRef.current;
    const response = await checkGeminiTailoringSetup();
    if (requestGenerationRef.current === generation) {
      setAvailability((current) => current.state === "loaded"
        ? { state: "loaded", providers: { ...current.providers, gemini: providerAccount(response) } }
        : current);
    }
    return response;
  }, []);

  return { availability, refresh, connect, disconnect, checkGemini };
}
