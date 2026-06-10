import React from "react";
import { cn } from "../../lib/utils";

export const GlassPanel: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => (
  <div className={cn(
    "rounded-2xl border border-white/5 bg-surface/50 backdrop-blur-md shadow-premium-lg",
    className
  )}>
    {children}
  </div>
);
