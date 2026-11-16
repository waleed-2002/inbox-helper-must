import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// Adapted from the shadcn/ui New York button registry item.
const buttonVariants = cva("button inline-flex shrink-0 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0", {
  variants: {
    variant: {
      default: "button-primary",
      outline: "button-outline",
      ghost: "button-ghost",
      destructive: "button-destructive",
    },
    size: { default: "min-h-9", icon: "size-9 px-0" },
  },
  defaultVariants: { variant: "default", size: "default" },
});

export function Button({ className, variant, size, asChild, type = "button", ...props }:
  React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : "button";
  return <Component type={type} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
