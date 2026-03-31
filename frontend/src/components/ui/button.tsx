import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition focus-visible:outline-none",
  {
    variants: {
      variant: {
        primary: "bg-navy text-white hover:bg-[#162b45]",
        secondary: "border border-border bg-white text-ink hover:bg-slate-50",
      },
    },
    defaultVariants: {
      variant: "primary",
    },
  },
);

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, ...props }, ref) => (
  <button ref={ref} className={cn(buttonVariants({ variant }), className)} {...props} />
));
Button.displayName = "Button";
