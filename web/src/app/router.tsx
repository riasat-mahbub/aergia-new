import type { ComponentType } from "react";
import { createBrowserRouter, createRoutesFromElements, Route } from "react-router-dom";
import RootLayout from "./layout";
import Loading from "./loading";

type RouteModule = { default: ComponentType };

/** Adapt a page module to React Router's route-level lazy contract. */
function lazyRoute(load: () => Promise<RouteModule>) {
  return async () => {
    const module = await load();
    return { Component: module.default, HydrateFallback: Loading };
  };
}

const router = createBrowserRouter(
  createRoutesFromElements(
    <Route element={<RootLayout />}>
      <Route index lazy={lazyRoute(() => import("./page"))} />
      <Route path="/login" lazy={lazyRoute(() => import("./login/page"))} />
      <Route path="/register" lazy={lazyRoute(() => import("./register/page"))} />
      <Route path="/agent/tailor/:sessionId" lazy={lazyRoute(() => import("./agent/tailor/[sessionId]/page"))} />
      <Route lazy={lazyRoute(() => import("./dashboard/layout"))}>
        <Route path="/builder/:id" lazy={lazyRoute(() => import("./builder/[id]/page"))} />
      </Route>
      <Route path="/dashboard" lazy={lazyRoute(() => import("./dashboard/layout"))}>
        <Route index lazy={lazyRoute(() => import("./dashboard/page"))} />
        <Route path="cvs" lazy={lazyRoute(() => import("./dashboard/cvs/page"))} />
        <Route path="library" lazy={lazyRoute(() => import("./dashboard/library/page"))} />
        <Route path="applications" lazy={lazyRoute(() => import("./dashboard/applications/page"))} />
        <Route path="applications/:id" lazy={lazyRoute(() => import("./dashboard/applications/[id]/page"))} />
        <Route path="settings" lazy={lazyRoute(() => import("./dashboard/settings/page"))} />
      </Route>
      <Route path="*" lazy={lazyRoute(() => import("./not-found"))} />
    </Route>,
  ),
);

export default router;
