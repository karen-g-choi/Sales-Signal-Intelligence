import * as React from "react";

import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-11 w-full rounded-xl border border-border bg-white px-4 text-sm text-ink outline-none transition placeholder:text-muted focus:border-slateblue",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
