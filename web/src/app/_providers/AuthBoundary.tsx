import { useEffect, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "@/lib/routerCompat";
import { useAuthStore } from "@/store/authStore";

interface AuthBoundaryProps {
  children: ReactNode;
}

export default function AuthBoundary({ children }: AuthBoundaryProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const hydrate = useAuthStore((state) => state.hydrate);
  const location = useLocation();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    let active = true;
    void hydrate().finally(() => {
      if (active) setHydrated(true);
    });
    return () => {
      active = false;
    };
  }, [hydrate]);

  if (!hydrated) return null;

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
