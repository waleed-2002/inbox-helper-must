import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

// Adapted from the shadcn/ui New York input and textarea registry items.
export function Input({ className, ...props }: ComponentProps<"input">) {
  return <input className={cn("field", className)} {...props} />;
}

export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return <textarea className={cn("field textarea", className)} {...props} />;
}
