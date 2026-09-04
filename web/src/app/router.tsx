import { createBrowserRouter, createRoutesFromElements, Route } from "react-router-dom";
import RootLayout from "./layout";
import HomePage from "./page";
import LoginPage from "./login/page";
import RegisterPage from "./register/page";
import AgentTailoringPage from "./agent/tailor/[sessionId]/page";
import DashboardLayout from "./dashboard/layout";
import DashboardPage from "./dashboard/page";
import CvListPage from "./dashboard/cvs/page";
import LibraryPage from "./dashboard/library/page";
import ApplicationsPage from "./dashboard/applications/page";
import ApplicationDetailPage from "./dashboard/applications/[id]/page";
import BuilderPage from "./builder/[id]/page";
import SettingsPage from "./dashboard/settings/page";
import NotFoundPage from "./not-found";

const router = createBrowserRouter(
  createRoutesFromElements(
    <Route element={<RootLayout />}>
      <Route index element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/agent/tailor/:sessionId" element={<AgentTailoringPage />} />
      <Route element={<DashboardLayout />}>
        <Route path="/builder/:id" element={<BuilderPage />} />
      </Route>
      <Route path="/dashboard" element={<DashboardLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="cvs" element={<CvListPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="applications" element={<ApplicationsPage />} />
        <Route path="applications/:id" element={<ApplicationDetailPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Route>,
  ),
);

export default router;
