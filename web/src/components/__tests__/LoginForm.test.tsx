import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
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
  const router = createMemoryRouter([
    { path: "/", element: <LoginForm /> },
  ]);
  return render(<RouterProvider router={router} />);
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

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "not-an-email" } });
    fireEvent.submit(screen.getByRole("button", { name: /sign in/i }).closest("form")!);

    expect(await screen.findByText(/invalid email/i)).toBeDefined();
  });

  it("shows register link", () => {
    renderLoginForm();
    expect(screen.getByText(/register/i)).toBeDefined();
  });
});
