export interface NavItem {
  path: string;
  label: string;
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  { path: "/", label: "Dashboard", description: "Case overview and system status." },
  { path: "/evidence", label: "Evidence", description: "Evidence intake, identification and hashing." },
  { path: "/investigation", label: "Investigation", description: "Metadata, integrity, steganalysis, watermark and comparison findings for one evidence item." },
  { path: "/steganography", label: "Steganography", description: "Conceal and extract data in a cover image." },
  { path: "/steganalysis", label: "Steganalysis", description: "Statistical LSB analysis: channel statistics, histograms, chi-square, RS." },
  { path: "/watermarking", label: "Watermarking", description: "Spatial and DCT watermarks, method comparison and robustness testing." },
  { path: "/comparison", label: "Comparison", description: "Reference vs derived or suspected image." },
  { path: "/provenance", label: "Provenance", description: "Derived artifacts, operations, analyses and timeline." },
  { path: "/reports", label: "Reports", description: "Forensic assessment and reporting." },
];

/** Routes that are still placeholders. */
export const PLACEHOLDER_PATHS = ["/reports"];
