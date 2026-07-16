import Image from "next/image";
import { cn } from "@/lib/utils";

export const BRAND_LOGO_SRC = "/brand/impactflow-logo.png";
export const BRAND_LOGO_ALT = "ImpactFlow";

type BrandLogoProps = {
  className?: string;
  /** Icon-only mark size in pixels (width & height). */
  size?: number;
  priority?: boolean;
  /** Show product name beside the mark. */
  withWordmark?: boolean;
  wordmark?: string;
  wordmarkClassName?: string;
};

export function BrandLogo({
  className,
  size = 36,
  priority = false,
  withWordmark = false,
  wordmark,
  wordmarkClassName,
}: BrandLogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <Image
        src={BRAND_LOGO_SRC}
        alt={BRAND_LOGO_ALT}
        width={size}
        height={size}
        priority={priority}
        className="shrink-0 rounded-[22%] object-contain"
      />
      {withWordmark && wordmark ? (
        <span
          className={cn(
            "font-display text-xl font-semibold tracking-tight text-teal-900 dark:text-teal-100",
            wordmarkClassName,
          )}
        >
          {wordmark}
        </span>
      ) : null}
    </span>
  );
}
