import { Component, type ReactNode } from "react";
import { Link } from "react-router-dom";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-app-canvas px-4">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-app-ink">Something went wrong</h1>
            <p className="mt-2 text-sm text-app-ink-3">
              An unexpected error occurred
            </p>
            <Link
              to="/dashboard"
              className="mt-6 inline-block rounded-md bg-app-primary px-4 py-2 text-sm text-white hover:bg-app-primary-hover"
              onClick={() => this.setState({ hasError: false })}
            >
              Go to Dashboard
            </Link>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
