import { useEffect, useState } from "react";
import { motion } from "motion/react";
import ProfileCard from "../components/profile/ProfileCard";
import { useAuthStore } from "../lib/store/authStore";
import { useProfileStore } from "../lib/store/profileStore";
import { useToastStore } from "../lib/store/uiStore";
import { PASSWORD_MIN_LENGTH } from "../lib/validators/auth";

export default function SettingsPage() {
  const changePassword = useAuthStore((s) => s.changePassword);
  const profile = useProfileStore((s) => s.profile);
  const profileLoading = useProfileStore((s) => s.isLoading);
  const profileLoaded = useProfileStore((s) => s.loaded);
  const fetchProfile = useProfileStore((s) => s.fetch);
  const updateProfile = useProfileStore((s) => s.update);
  const addToast = useToastStore((s) => s.addToast);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!profileLoaded) fetchProfile();
  }, [fetchProfile, profileLoaded]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (newPassword.length < PASSWORD_MIN_LENGTH) {
      setError(`Password must be at least ${PASSWORD_MIN_LENGTH} characters`);
      return;
    }

    setLoading(true);
    try {
      await changePassword(currentPassword, newPassword);
      addToast("Password changed successfully", "success");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch {
      setError("Failed to change password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-lg px-4 py-8"
    >
      <h1 className="mb-6 text-2xl font-bold text-app-ink">Settings</h1>

      <ProfileCard
        profile={profile}
        isLoading={profileLoading}
        onSave={updateProfile}
        eyebrow="Settings Profile"
        description="Shared profile details used when building your CVs."
        testId="settings-profile-card"
      />

      <div className="rounded-lg bg-app-surface p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-app-ink">Change Password</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="current-password" className="block text-sm font-medium text-app-ink-2">Current Password</label>
            <input
              id="current-password"
              name="current_password"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border border-app-rule-strong px-3 py-2 text-sm shadow-sm focus:border-app-primary focus:outline-none focus:ring-1 focus:ring-app-primary"
            />
          </div>
          <div>
            <label htmlFor="new-password" className="block text-sm font-medium text-app-ink-2">New Password</label>
            <input
              id="new-password"
              name="new_password"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border border-app-rule-strong px-3 py-2 text-sm shadow-sm focus:border-app-primary focus:outline-none focus:ring-1 focus:ring-app-primary"
            />
          </div>
          <div>
            <label htmlFor="confirm-new-password" className="block text-sm font-medium text-app-ink-2">Confirm New Password</label>
            <input
              id="confirm-new-password"
              name="confirm_new_password"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border border-app-rule-strong px-3 py-2 text-sm shadow-sm focus:border-app-primary focus:outline-none focus:ring-1 focus:ring-app-primary"
            />
          </div>
          {error && <p className="text-sm text-app-danger">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-app-primary px-4 py-2 text-sm text-white hover:bg-app-primary-hover disabled:opacity-50"
          >
            {loading ? "Changing..." : "Change Password"}
          </button>
        </form>
      </div>
    </motion.div>
  );
}
