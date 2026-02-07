import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import RegisterForm from "../auth/RegisterForm";

vi.mock("../../lib/store/authStore", () => ({
  useAuthStore: vi.fn((selector) =>
    selector({
      register: vi.fn(),
      isLoading: false,
    })
  ),
}));

function renderRegisterForm() {
  return render(
    <BrowserRouter>
      <RegisterForm />
    </BrowserRouter>
  );
}

describe("RegisterForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
});
