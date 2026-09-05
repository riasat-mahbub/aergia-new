import { useCallback, useEffect, useMemo } from "react";
import {
  Link as TanStackLink,
  Outlet,
  useBlocker as useTanStackBlocker,
  useNavigate as useTanStackNavigate,
  useRouterState,
} from "@tanstack/react-router";
import type { AnchorHTMLAttributes, ReactNode } from "react";

export { Outlet };

type NavigateOptions = { replace?: boolean; state?: unknown };

export function useNavigate() {
  const navigate = useTanStackNavigate();
  return useCallback(
    (to: string, options?: NavigateOptions) => {
      void navigate({ to: to as never, replace: options?.replace });
    },
    [navigate],
  );
}

export function useParams<T extends Record<string, string | undefined> = Record<string, string | undefined>>() {
  const params = useRouterState({
    select: (state) => state.matches.reduce<Record<string, string | undefined>>(
      (params, match) => ({ ...params, ...match.params }),
      {},
    ),
  });
  return params as T;
}

export function useLocation() {
  return useRouterState({
    select: (state) => ({
      pathname: state.location.pathname,
      search: state.location.searchStr,
      href: state.location.href,
    }),
  });
}

export function useSearchParams(): [URLSearchParams] {
  const { search } = useLocation();
  const params = useMemo(() => new URLSearchParams(search), [search]);
  return [params];
}

interface LinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> {
  to: string;
  children?: ReactNode;
  replace?: boolean;
}

export function Link({ to, replace, children, ...props }: LinkProps) {
  return (
    <TanStackLink to={to as never} replace={replace} {...props}>
      {children}
    </TanStackLink>
  );
}

interface NavLinkProps extends Omit<LinkProps, "className"> {
  end?: boolean;
  className?: string | ((args: { isActive: boolean; isPending: boolean }) => string);
}

export function NavLink({ to, end = false, className, ...props }: NavLinkProps) {
  const { pathname } = useLocation();
  const isActive = end ? pathname === to : pathname === to || pathname.startsWith(`${to}/`);
  const resolvedClassName = typeof className === "function"
    ? className({ isActive, isPending: false })
    : className;
  return <Link to={to} className={resolvedClassName} {...props} />;
}

export function Navigate({ to, replace }: { to: string; replace?: boolean; state?: unknown }) {
  const navigate = useNavigate();
  useEffect(() => {
    navigate(to, { replace });
  }, [navigate, replace, to]);
  return null;
}

export function useBlocker(
  blocker: (args: {
    currentLocation: { pathname: string };
    nextLocation: { pathname: string };
  }) => boolean,
) {
  const resolver = useTanStackBlocker({
    withResolver: true,
    shouldBlockFn: ({ current, next }) => blocker({
      currentLocation: { pathname: current.pathname },
      nextLocation: { pathname: next.pathname },
    }),
  });
  return {
    state: resolver.status,
    proceed: resolver.proceed ?? (() => undefined),
    reset: resolver.reset ?? (() => undefined),
  };
}
