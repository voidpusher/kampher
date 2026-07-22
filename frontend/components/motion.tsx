"use client";

import {
  motion,
  type MotionValue,
  useMotionValue,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
} from "framer-motion";
import { createContext, useContext, useRef, useState } from "react";

/**
 * A shared perspective stage. Tracks the pointer across its own bounds and
 * broadcasts a centered (-0.5..0.5) position to any SceneLayer inside it, so
 * many layers can parallax together against one real 3D camera.
 */
const SceneContext = createContext<{
  px: MotionValue<number>;
  py: MotionValue<number>;
} | null>(null);

export function Scene({
  children,
  className = "",
  perspective = 1000,
}: {
  children: React.ReactNode;
  className?: string;
  perspective?: number;
}) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const px = useMotionValue(0);
  const py = useMotionValue(0);

  if (reduced) {
    return <div className={className}>{children}</div>;
  }
  return (
    <div
      className={className}
      onPointerLeave={() => {
        px.set(0);
        py.set(0);
      }}
      onPointerMove={(event) => {
        const bounds = ref.current?.getBoundingClientRect();
        if (!bounds) return;
        px.set((event.clientX - bounds.left) / bounds.width - 0.5);
        py.set((event.clientY - bounds.top) / bounds.height - 0.5);
      }}
      ref={ref}
      style={{ perspective, transformStyle: "preserve-3d" }}
    >
      <SceneContext.Provider value={{ px, py }}>
        {children}
      </SceneContext.Provider>
    </div>
  );
}

/**
 * A single depth plane inside a Scene. `depth` is how far the layer sits from
 * the camera in px on Z (positive = nearer, larger, and drifts more with the
 * pointer). This is genuine perspective parallax, not a 2D fake.
 */
export function SceneLayer({
  children,
  depth = 24,
  className = "",
}: {
  children: React.ReactNode;
  depth?: number;
  className?: string;
}) {
  const ctx = useContext(SceneContext);
  const reduced = useReducedMotion();
  const zeroX = useMotionValue(0);
  const zeroY = useMotionValue(0);
  const px = ctx?.px ?? zeroX;
  const py = ctx?.py ?? zeroY;
  const x = useSpring(useTransform(px, (value) => value * depth * 1.6), {
    stiffness: 140,
    damping: 20,
  });
  const y = useSpring(useTransform(py, (value) => value * depth * 1.6), {
    stiffness: 140,
    damping: 20,
  });

  if (reduced || !ctx) {
    return <div className={className}>{children}</div>;
  }
  return (
    <motion.div
      className={className}
      style={{ x, y, translateZ: depth, transformStyle: "preserve-3d" }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Pointer-tracking 3D tilt with spring physics. Children stay
 * server-rendered; this only wraps them in a perspective stage.
 */
export function Tilt3D({
  children,
  maxDeg = 7,
  className = "",
}: {
  children: React.ReactNode;
  maxDeg?: number;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const pointerX = useMotionValue(0.5);
  const pointerY = useMotionValue(0.5);
  const rotateX = useSpring(useTransform(pointerY, [0, 1], [maxDeg, -maxDeg]), {
    stiffness: 220,
    damping: 18,
  });
  const rotateY = useSpring(useTransform(pointerX, [0, 1], [-maxDeg, maxDeg]), {
    stiffness: 220,
    damping: 18,
  });

  if (reduced) {
    return <div className={className}>{children}</div>;
  }

  return (
    <div className={className} style={{ perspective: 900 }}>
      <motion.div
        onPointerLeave={() => {
          pointerX.set(0.5);
          pointerY.set(0.5);
        }}
        onPointerMove={(event) => {
          const bounds = ref.current?.getBoundingClientRect();
          if (!bounds) return;
          pointerX.set((event.clientX - bounds.left) / bounds.width);
          pointerY.set((event.clientY - bounds.top) / bounds.height);
        }}
        ref={ref}
        style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
      >
        {children}
      </motion.div>
    </div>
  );
}

/**
 * Scroll parallax: children drift vertically at `speed` relative to scroll.
 * Positive speed lags (feels far away), negative leads (feels close).
 */
export function Parallax({
  children,
  speed = 0.2,
  className = "",
}: {
  children: React.ReactNode;
  speed?: number;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    offset: ["start end", "end start"],
    target: ref,
  });
  const y = useTransform(scrollYProgress, [0, 1], [speed * 140, speed * -140]);

  if (reduced) {
    return <div className={className}>{children}</div>;
  }
  return (
    <motion.div className={className} ref={ref} style={{ y }}>
      {children}
    </motion.div>
  );
}

/** Hover-flip card: front face rotates away to reveal a back face. */
export function FlipCard({
  front,
  back,
  className = "",
}: {
  front: React.ReactNode;
  back: React.ReactNode;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const [flipped, setFlipped] = useState(false);

  if (reduced) {
    return <div className={className}>{front}</div>;
  }
  return (
    <div
      className={className}
      onBlur={() => setFlipped(false)}
      onFocus={() => setFlipped(true)}
      onPointerEnter={() => setFlipped(true)}
      onPointerLeave={() => setFlipped(false)}
      style={{ perspective: 1000 }}
      tabIndex={0}
    >
      <motion.div
        animate={{ rotateY: flipped ? 180 : 0 }}
        className="relative"
        style={{ transformStyle: "preserve-3d" }}
        transition={{ type: "spring", stiffness: 170, damping: 18 }}
      >
        <div style={{ backfaceVisibility: "hidden" }}>{front}</div>
        <div
          className="absolute inset-0"
          style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}
        >
          {back}
        </div>
      </motion.div>
    </div>
  );
}

/** Slowly spinning solid starburst — pure fun, pure ink. */
export function SpinBadge({
  label,
  className = "",
}: {
  label: string;
  className?: string;
}) {
  const reduced = useReducedMotion();
  return (
    <div className={`relative grid place-items-center ${className}`}>
      <motion.svg
        animate={reduced ? undefined : { rotate: 360 }}
        aria-hidden="true"
        height="150"
        transition={{ duration: 14, ease: "linear", repeat: Infinity }}
        viewBox="0 0 100 100"
        width="150"
      >
        <polygon
          fill="#FFE600"
          points={starburst(16, 50, 34)}
          stroke="#0A0A0A"
          strokeWidth="2.5"
        />
      </motion.svg>
      <span className="absolute max-w-[90px] text-center font-mono text-[10px] font-bold uppercase leading-tight tracking-[0.06em]">
        {label}
      </span>
    </div>
  );
}

function starburst(spikes: number, outer: number, inner: number): string {
  const points: string[] = [];
  for (let index = 0; index < spikes * 2; index += 1) {
    const radius = index % 2 === 0 ? outer : inner;
    const angle = (Math.PI * index) / spikes;
    points.push(`${50 + radius * Math.cos(angle)},${50 + radius * Math.sin(angle)}`);
  }
  return points.join(" ");
}

/** Flip-up scroll entrance: content rotates in from below with a spring. */
export function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const reduced = useReducedMotion();
  if (reduced) {
    return <div className={className}>{children}</div>;
  }
  return (
    <div className={className} style={{ perspective: 1100 }}>
      <motion.div
        initial={{ opacity: 0, y: 48, rotateX: 18 }}
        transition={{ type: "spring", stiffness: 130, damping: 17, delay }}
        viewport={{ margin: "-60px", once: true }}
        whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
      >
        {children}
      </motion.div>
    </div>
  );
}
