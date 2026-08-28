import RegisterForm from "../components/auth/RegisterForm";

export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-app-canvas px-4">
      <div className="w-full max-w-md rounded-lg bg-app-surface p-8 shadow-md">
        <h1 className="mb-6 text-center text-2xl font-bold text-app-ink">Create an account</h1>
        <RegisterForm />
      </div>
    </div>
  );
}
