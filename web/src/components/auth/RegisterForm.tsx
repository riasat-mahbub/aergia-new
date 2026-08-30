import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { registerSchema, type RegisterFormData } from "../../lib/validators/auth";
import { useAuthStore } from "../../lib/store/authStore";
import { getRegistrationConfig, type RegistrationConfig } from "../../lib/api/auth";
import TurnstileWidget from "./TurnstileWidget";

export default function RegisterForm() {
  const navigate = useNavigate();
  const registerUser = useAuthStore((s) => s.register);
  const isLoading = useAuthStore((s) => s.isLoading);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [config, setConfig] = useState<RegistrationConfig | null>(null);
  const [configError, setConfigError] = useState(false);
  const [configLoading, setConfigLoading] = useState(true);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [widgetError, setWidgetError] = useState(false);
  const [widgetResetKey, setWidgetResetKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void getRegistrationConfig()
      .then((registrationConfig) => {
        if (!cancelled) {
          setConfig(registrationConfig);
          setConfigError(false);
        }
      })
      .catch(() => {
        if (!cancelled) setConfigError(true);
      })
      .finally(() => {
        if (!cancelled) setConfigLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleTurnstileToken = useCallback((token: string) => {
    setTurnstileToken(token || null);
    setWidgetError(false);
  }, []);

  const handleTurnstileError = useCallback(() => {
    setTurnstileToken(null);
    setWidgetError(true);
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setError(null);
    if (!config || configError || (config.turnstile_required && !turnstileToken)) {
      setError("Please complete the security verification.");
      return;
    }
    try {
      await registerUser(data.email, data.password, turnstileToken ?? undefined);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch {
      setError("Registration failed. Email may already be in use.");
      setTurnstileToken(null);
      setWidgetResetKey((key) => key + 1);
    }
  };

  if (success) {
    return (
      <div className="text-center">
        <p className="text-app-success font-medium">Account created successfully!</p>
        <p className="text-sm text-app-ink-3 mt-2">Redirecting to login...</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-app-ink-2">Email</label>
        <input
          id="email"
          type="email"
          {...register("email")}
          className="mt-1 block w-full rounded-md border border-app-rule-strong px-3 py-2 shadow-sm focus:border-app-primary focus:outline-none focus:ring-1 focus:ring-app-primary"
        />
        {errors.email && <p className="mt-1 text-sm text-app-danger">{errors.email.message}</p>}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-app-ink-2">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          {...register("password")}
          className="mt-1 block w-full rounded-md border border-app-rule-strong px-3 py-2 shadow-sm focus:border-app-primary focus:outline-none focus:ring-1 focus:ring-app-primary"
        />
        {errors.password && <p className="mt-1 text-sm text-app-danger">{errors.password.message}</p>}
      </div>

      <div>
        <label htmlFor="confirmPassword" className="block text-sm font-medium text-app-ink-2">Confirm Password</label>
        <input
          id="confirmPassword"
          type="password"
          autoComplete="new-password"
          {...register("confirmPassword")}
          className="mt-1 block w-full rounded-md border border-app-rule-strong px-3 py-2 shadow-sm focus:border-app-primary focus:outline-none focus:ring-1 focus:ring-app-primary"
        />
        {errors.confirmPassword && <p className="mt-1 text-sm text-app-danger">{errors.confirmPassword.message}</p>}
      </div>

      {configLoading && <p className="text-sm text-app-ink-3">Loading security verification...</p>}
      {config?.turnstile_site_key && !configLoading && (
        <TurnstileWidget
          siteKey={config.turnstile_site_key}
          action={config.turnstile_action}
          resetKey={widgetResetKey}
          onToken={handleTurnstileToken}
          onError={handleTurnstileError}
        />
      )}
      {!configLoading && configError && (
        <p className="text-sm text-app-danger" role="alert">Security verification is unavailable.</p>
      )}
      {!configLoading && config?.turnstile_required && !config.turnstile_site_key && !configError && (
        <p className="text-sm text-app-danger" role="alert">Security verification is unavailable.</p>
      )}
      {widgetError && <p className="text-sm text-app-danger" role="alert">Please retry the security verification.</p>}

      {error && <p className="text-sm text-app-danger">{error}</p>}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-md bg-app-primary px-4 py-2 text-white hover:bg-app-primary-hover disabled:opacity-50"
      >
        {isLoading ? "Creating account..." : "Create account"}
      </button>

      <p className="text-center text-sm text-app-ink-2">
        Already have an account?{" "}
        <a href="/login" className="text-app-primary hover:underline">Sign in</a>
      </p>
    </form>
  );
}
