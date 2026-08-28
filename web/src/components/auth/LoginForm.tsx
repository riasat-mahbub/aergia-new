import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { loginSchema, type LoginFormData } from "../../lib/validators/auth";
import { useAuthStore } from "../../lib/store/authStore";
import { useState } from "react";

export default function LoginForm() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const isLoading = useAuthStore((s) => s.isLoading);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setError(null);
    try {
      await login(data.email, data.password);
      navigate("/dashboard", { replace: true });
    } catch {
      setError("Invalid email or password");
    }
  };

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
          autoComplete="current-password"
          {...register("password")}
          className="mt-1 block w-full rounded-md border border-app-rule-strong px-3 py-2 shadow-sm focus:border-app-primary focus:outline-none focus:ring-1 focus:ring-app-primary"
        />
        {errors.password && <p className="mt-1 text-sm text-app-danger">{errors.password.message}</p>}
      </div>

      {error && <p className="text-sm text-app-danger">{error}</p>}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-md bg-app-primary px-4 py-2 text-white hover:bg-app-primary-hover disabled:opacity-50"
      >
        {isLoading ? "Signing in..." : "Sign in"}
      </button>

      <p className="text-center text-sm text-app-ink-2">
        Don't have an account?{" "}
        <a href="/register" className="text-app-primary hover:underline">Register</a>
      </p>
    </form>
  );
}
