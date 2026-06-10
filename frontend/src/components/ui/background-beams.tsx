import { useEffect, useRef } from "react";
import { cn } from "../../lib/utils";

export const BackgroundBeams = ({ className }: { className?: string }) => {
  const beamsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const beams = beamsRef.current;
    if (!beams) return;

    const moveBeams = (e: MouseEvent) => {
      const { clientX, clientY } = e;
      beams.style.setProperty("--x", `${clientX}px`);
      beams.style.setProperty("--y", `${clientY}px`);
    };

    window.addEventListener("mousemove", moveBeams);
    return () => window.removeEventListener("mousemove", moveBeams);
  }, []);

  return (
    <div
      ref={beamsRef}
      className={cn(
        "absolute inset-0 z-0 opacity-40 pointer-events-none overflow-hidden",
        className
      )}
      style={{
        background: "radial-gradient(600px circle at var(--x, 50%) var(--y, 50%), rgba(255,255,255,0.06), transparent 40%)",
      }}
    >
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
    </div>
  );
};
