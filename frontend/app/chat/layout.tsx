import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ask the index",
  description: "Turn indexed technical conversations into cited problems worth solving.",
};

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return children;
}
