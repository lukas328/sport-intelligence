"use client";

import { useShirt } from "@/components/kit";
import type { Shirt } from "@/lib/product-shots";

/** the files of a picture in one colour */
export type ShotFiles = { src: string; srcSet: string };

/**
 * The picture of a ProductShot in the visitor's shirt colour (BEFUNDE-4 U45): the app pictures
 * are made in each club colour, and the one of the shirt picked in the header (useShirt) is shown.
 * Only that one loads; when the shirt changes, the browser keeps the old picture until the new
 * one is there. Without a pick, or without JavaScript, the demo club's green (`files.green`).
 */
export function ShotImage({
  files,
  phoneFiles,
  phoneMedia,
  sizes,
  phoneSizes,
  width,
  height,
  phoneWidth,
  phoneHeight,
  alt,
  priority,
}: {
  /** by shirt; `green` is the default */
  files: Partial<Record<Shirt, ShotFiles>> & { green: ShotFiles };
  phoneFiles?: Partial<Record<Shirt, ShotFiles>> & { green: ShotFiles };
  phoneMedia: string;
  sizes: string;
  phoneSizes: string;
  width: number;
  height: number;
  phoneWidth?: number;
  phoneHeight?: number;
  alt: string;
  priority: boolean;
}) {
  const { shirt } = useShirt();
  const pick = <T,>(by: Partial<Record<Shirt, T>> & { green: T }) => (shirt && by[shirt]) || by.green;
  const main = pick(files);
  const img = (
    <img
      src={main.src}
      srcSet={main.srcSet}
      sizes={sizes}
      alt={alt}
      width={width}
      height={height}
      loading={priority ? "eager" : "lazy"}
      decoding="async"
      className="block h-auto w-full"
    />
  );
  if (!phoneFiles) return img;
  // art direction: the phone picture under 40rem, each with its own size, so nothing moves
  return (
    <picture>
      <source media={phoneMedia} srcSet={pick(phoneFiles).srcSet} sizes={phoneSizes} width={phoneWidth} height={phoneHeight} />
      {img}
    </picture>
  );
}
