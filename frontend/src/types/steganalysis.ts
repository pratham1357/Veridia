/** Mirrors backend/app/schemas/steganalysis.py. Keep in sync. */
import type { ImageSummary } from "./evidence";

export type Channel = "red" | "green" | "blue";

export interface RsStats {
  r_m: number | null;
  s_m: number | null;
  r_neg_m: number | null;
  s_neg_m: number | null;
  estimate: number | null;
}

export interface ChannelSteganalysis {
  channel: Channel;
  mean: number;
  std: number;
  entropy_bits: number;
  ones_ratio: number;
  transition_ratio: number;
  chi_square_p: number | null;
  rs: RsStats;
}

export interface SteganalysisReport {
  image_id: string;
  channels: ChannelSteganalysis[];
  histograms: Record<Channel, number[]>;
  chi_square: {
    chi2: number | null;
    degrees_of_freedom: number;
    p_value: number | null;
    curve: { fraction: number; p_value: number | null }[];
    consistent_prefix_fraction: number;
  };
  rs_mean_estimate: number | null;
  lsb_capacity_bytes: number;
  prefix_payload_bytes_upper: number;
  veridia_lsb_header_found: boolean;
  indicators: string[];
  disclaimer: string;
}

export interface CoverComparison {
  cover: ImageSummary;
  suspect: ImageSummary;
  total_samples: number;
  changed_samples: number;
  changed_fraction: number;
  max_abs_difference: number;
  lsb_only: boolean;
  changed_per_channel: Record<Channel, number>;
  first_changed_index: number | null;
  last_changed_index: number | null;
}
