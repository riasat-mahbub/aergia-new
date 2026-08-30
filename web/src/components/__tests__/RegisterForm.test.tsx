import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import RegisterForm from "../auth/RegisterForm";

const { mockRegister, mockGetRegistrationConfig } = vi.hoisted(() => ({
  mockRegister: vi.fn(),
  mockGetRegistrationConfig: vi.fn(),
}));

vi.mock("../../lib/store/authStore", () => ({
  useAuthStore: vi.fn((selector) =>
    selector({
      register: mockRegister,
      isLoading: false,
    })
  ),
}));

vi.mock("../../lib/api/auth", () => ({
  getRegistrationConfig: mockGetRegistrationConfig,
}));

function renderRegisterForm() {
  const router = createMemoryRouter([
    { path: "/", element: <RegisterForm /> },
  ]);
  return render(<RouterProvider router={router} />);
}

describe("RegisterForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetRegistrationConfig.mockResolvedValue({
      turnstile_site_key: null,
      turnstile_required: false,
      turnstile_action: "register",
    });
    mockRegister.mockResolvedValue(undefined);
    window.turnstile = undefined;
  });

  it("renders all fields and submit button", () => {
    renderRegisterForm();
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(screen.getByLabelText(/^password$/i)).toBeDefined();
    expect(screen.getByLabelText(/confirm password/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /create account/i })).toBeDefined();
  });

  it("shows validation error for short password", async () => {
    renderRegisterForm();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "short");
    await user.type(screen.getByLabelText(/confirm password/i), "short");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/at least 8 characters/i)).toBeDefined();
    });
  });

  it("shows validation error when passwords do not match", async () => {
    renderRegisterForm();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "password123");
    await user.type(screen.getByLabelText(/confirm password/i), "different");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeDefined();
    });
  });

  it("shows sign in link", () => {
    renderRegisterForm();
    expect(screen.getByText(/sign in/i)).toBeDefined();
  });

  it("passes a Turnstile token to registration and resets it after a failed attempt", async () => {
    mockGetRegistrationConfig.mockResolvedValueOnce({
      turnstile_site_key: "site-key",
      turnstile_required: true,
      turnstile_action: "register",
    });
    mockRegister.mockRejectedValueOnce(new Error("rejected"));
    const reset = vi.fn();
    window.turnstile = {
      render: (_container, options) => {
        options.callback?.("turnstile-token");
        return "widget-id";
      },
      reset,
      remove: vi.fn(),
    };

    renderRegisterForm();
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByLabelText(/security verification/i)).toBeDefined());
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "password123");
    await user.type(screen.getByLabelText(/confirm password/i), "password123");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(mockRegister).toHaveBeenCalledWith(
      "test@example.com",
      "password123",
      "turnstile-token",
    ));
    await waitFor(() => expect(reset).toHaveBeenCalledWith("widget-id"));
  });
});
