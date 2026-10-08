import type { Operation } from "../types/evidence";
import type { WatermarkMethod } from "../types/watermark";

export const OPERATION_LABEL: Record<Operation, string> = {
  lsb_steganography_embed: "LSB steganography embed",
  watermark_embed: "Spatial (LSB) watermark embed",
  dct_watermark_embed: "DCT watermark embed",
  attack: "Attack (robustness experiment)",
};

export const OUTPUT_LABEL: Record<Operation, string> = {
  lsb_steganography_embed: "Stego image",
  watermark_embed: "Spatial-watermarked image",
  dct_watermark_embed: "DCT-watermarked image",
  attack: "Attacked image",
};

export const METHOD_LABEL: Record<WatermarkMethod, string> = {
  spatial_lsb: "Spatial domain (LSB)",
  dct: "Transform domain (DCT)",
};

export const MAX_MESSAGE_BYTES: Record<WatermarkMethod, number> = { spatial_lsb: 64, dct: 16 };
