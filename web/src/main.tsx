import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider, createRoutesFromElements, Route, Outlet } from "react-router-dom";
import App from "./App";
import HomePage from "./features/home/HomePage";
import ProtectedRoute from "./components/common/ProtectedRoute";
import AppLayout from "./components/common/AppLayout";
import LoginPage from "./features/login/LoginPage";
import RegisterPage from "./features/register/RegisterPage";
import DashboardPage from "./features/dashboard/DashboardPage";
import CvListPage from "./features/cv-list/CvListPage";
import LibraryPage from "./features/library/LibraryPage";
import ApplicationsPage from "./features/applications/ApplicationsPage";
import ApplicationDetailPage from "./features/application-detail/ApplicationDetailPage";
import BuilderPage from "./features/builder/BuilderPage";
import SettingsPage from "./features/settings/SettingsPage";
import NotFoundPage from "./pages/NotFoundPage";
import AgentTailoringPage from "./features/agent-tailoring/AgentTailoringPage";
import "./index.css";
import "react-day-picker/style.css";
const router = createBrowserRouter(
  createRoutesFromElements(
    <Route element={<App />}>
      <Route index element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/agent/tailor/:sessionId" element={<AgentTailoringPage />} />
      <Route
        path="/dashboard"
        element={<ProtectedRoute><AppLayout><Outlet /></AppLayout></ProtectedRoute>}
      >
        <Route index element={<DashboardPage />} />
        <Route path="cvs" element={<CvListPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="applications" element={<ApplicationsPage />} />
        <Route path="applications/:id" element={<ApplicationDetailPage />} />
        <Route path="builder/:id" element={<BuilderPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Route>
  )
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
