export interface NavItem {
  path: string;
  label: string;
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  { path: "/", label: "Dashboard", description: "Case overview and system status." },
  { path: "/evidence", label: "Evidence", description: "Evidence intake, identification and hashing." },
  { path: "/provenance", label: "Provenance", description: "Metadata and origin analysis." },
  { path: "/integrity", label: "Integrity", description: "Image integrity and manipulation indicators." },
  { path: "/steganography", label: "Steganography", description: "Hidden information analysis." },
  { path: "/watermarking", label: "Watermarking", description: "Watermark embedding, extraction and verification." },
  { path: "/reports", label: "Reports", description: "Forensic assessment and reporting." },
];
