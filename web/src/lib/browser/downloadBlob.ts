/** Trigger a browser download for a blob. Kept outside API services so they stay environment-agnostic. */
export function downloadBlob(blob: Blob, filename = "download") {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
