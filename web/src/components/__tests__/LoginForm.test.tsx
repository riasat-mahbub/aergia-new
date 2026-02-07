import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import LoginForm from "../auth/LoginForm";

vi.mock("../../lib/store/authStore", () => ({
  useAuthStore: vi.fn((selector) =>
    selector({
      login: vi.fn(),
      isLoading: false,
    })
  ),
}));

function renderLoginForm() {
  return render(
    <BrowserRouter>
      <LoginForm />
    </BrowserRouter>
  );
}

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders email and password fields", () => {
    renderLoginForm();
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(screen.getByLabelText(/password/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeDefined();
  });

  it("shows validation errors for empty fields", async () => {
    renderLoginForm();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeDefined();
    });
  });

  it("shows validation error for invalid email", async () => {
    renderLoginForm();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/email/i), "not-an-email");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeDefined();
    });
  });

  it("shows register link", () => {
    renderLoginForm();
    expect(screen.getByText(/register/i)).toBeDefined();
  });
});
