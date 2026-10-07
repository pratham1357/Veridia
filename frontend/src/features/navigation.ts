export interface NavItem {
  path: string;
  label: string;
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  { path: "/", label: "Dashboard", description: "Case overview and system status." },
  { path: "/evidence", label: "Evidence", description: "Evidence intake, identification and hashing." },
  { path: "/provenance", label: "Provenance", description: "Processing chain and hashes for the active evidence." },
  { path: "/integrity", label: "Integrity", description: "Image integrity and manipulation indicators." },
  { path: "/steganography", label: "Steganography", description: "Conceal and extract data in a cover image; inspect LSB planes." },
  { path: "/watermarking", label: "Watermarking", description: "Embed and verify an identifying watermark." },
  { path: "/comparison", label: "Comparison", description: "Original vs processed image with quality metrics." },
  { path: "/reports", label: "Reports", description: "Forensic assessment and reporting." },
];

/** Routes that are still placeholders. */
export const PLACEHOLDER_PATHS = ["/integrity", "/reports"];
