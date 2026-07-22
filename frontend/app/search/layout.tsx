import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Search the signal",
  description: "Search Kampher's indexed technical conversations by keyword or meaning.",
};

export default function SearchLayout({ children }: { children: React.ReactNode }) {
  return children;
}
