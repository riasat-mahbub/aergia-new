import { useState, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import client from "../../lib/api/client";

interface PhotoUploadProps {
  currentUrl?: string | null;
  onUpload: (url: string) => void;
}

export default function PhotoUpload({ currentUrl, onUpload }: PhotoUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(currentUrl || null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const { data } = await client.post("/assets", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setPreview(data.url);
      onUpload(data.url);
    } catch {
      alert("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex items-center gap-4">
      <AnimatePresence mode="wait">
        {preview ? (
          <motion.img
            key="preview"
            src={preview}
            alt="Profile"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="h-16 w-16 rounded-full object-cover"
          />
        ) : (
          <motion.div
            key="placeholder"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex h-16 w-16 items-center justify-center rounded-full bg-gray-100 text-gray-400"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </motion.div>
        )}
      </AnimatePresence>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="rounded border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
      >
        {uploading ? "Uploading..." : "Upload photo"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  );
}
