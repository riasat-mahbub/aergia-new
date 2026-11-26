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
  TailoringProviderStatusResponse,
  TailoringProvidersResponse,
} from "../types";

function providerAccount(response: TailoringProviderStatusResponse): TailoringProviderAccount {
  return { status: response.status, detail: response.detail };
}

export function useTailoringProviders() {
  const [providers, setProviders] = useState<TailoringProvidersResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestGenerationRef = useRef(0);

  const loadProviders = useCallback(() => {
    const generation = ++requestGenerationRef.current;
    return getTailoringProviders()
      .then((response) => {
        if (requestGenerationRef.current === generation) setProviders(response);
      })
      .catch(() => {
        if (requestGenerationRef.current === generation) {
          setError("Provider status could not be loaded. Try again in Settings.");
        }
      })
      .finally(() => {
        if (requestGenerationRef.current === generation) setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    void loadProviders();
    return () => { requestGenerationRef.current += 1; };
  }, [loadProviders]);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    await loadProviders();
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
    const response = await disconnectTailoringProvider(provider);
    setProviders((current) => current ? { ...current, [provider]: providerAccount(response) } : current);
    return response;
  }, []);

  const checkGemini = useCallback(async () => {
    const response = await checkGeminiTailoringSetup();
    setProviders((current) => current ? { ...current, gemini: providerAccount(response) } : current);
    return response;
  }, []);

  return { providers, isLoading, error, refresh, connect, disconnect, checkGemini };
}
