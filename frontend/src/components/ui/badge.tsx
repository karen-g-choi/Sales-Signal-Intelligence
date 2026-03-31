import type { HTMLAttributes } from "react";

import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold text-white",
  {
    variants: {
      variant: {
        stable: "bg-stable",
        watch: "bg-watch",
        warning: "bg-warning",
        critical: "bg-critical",
        muted: "bg-slateblue",
      },
    },
    defaultVariants: {
      variant: "muted",
    },
  },
);

export interface BadgeProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
