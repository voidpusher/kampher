"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ReactMarkdown from "react-markdown";

import { api, SOURCE_LABELS, type ChatResponse } from "@/lib/api";

interface Exchange {
  question: string;
  response: ChatResponse | null;
  pending: boolean;
  failed: boolean;
}

const STARTERS = [
  "What SaaS should I build in devtools?",
  "What are developers complaining about in authentication?",
  "Which problems are rapidly increasing this month?",
];

export default function ChatPage() {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [input, setInput] = useState("");
  const busy = exchanges.some((exchange) => exchange.pending);
  const bottomRef = useRef<HTMLDivElement>(null);

  async function ask(question: string) {
    if (!question.trim() || busy) return;
    setInput("");
    setExchanges((previous) => [
      ...previous,
      { question, response: null, pending: true, failed: false },
    ]);
    requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }));

    const response = await api.chat(question);
    setExchanges((previous) =>
      previous.map((exchange, index) =>
        index === previous.length - 1
          ? { ...exchange, response, pending: false, failed: response === null }
          : exchange,
      ),
    );
    requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }));
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-4xl flex-col px-4 py-12 sm:px-8 sm:py-16">
      <div className="border-b border-line pb-8">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-ember" />
          <p className="editorial-label">Evidence-bound intelligence</p>
        </div>
        <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          Ask the index
        </h1>
        <p className="mt-3 max-w-xl text-sm leading-6 text-muted">
          Answers use only Kampher&apos;s indexed conversations and opportunities,
          with the original evidence attached.
        </p>
      </div>

      <div className="mt-8 flex-1 space-y-10">
        {exchanges.length === 0 ? (
          <div className="grid gap-3 sm:grid-cols-3">
            {STARTERS.map((starter) => (
              <button
                className="group flex min-h-32 w-full flex-col justify-between rounded-xl border border-line bg-surface p-4 text-left text-sm leading-5 text-muted transition-all hover:-translate-y-0.5 hover:border-muted hover:text-fg"
                key={starter}
                onClick={() => void ask(starter)}
                type="button"
              >
                <span>{starter}</span>
                <span className="self-end font-mono text-xs text-ember transition-transform group-hover:translate-x-1">→</span>
              </button>
            ))}
          </div>
        ) : null}

        <AnimatePresence>
          {exchanges.map((exchange, index) => (
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
              initial={{ opacity: 0, y: 10 }}
              key={`${exchange.question}-${index}`}
            >
              <div className="flex items-start gap-3">
                <span className="mt-1 grid h-6 w-6 shrink-0 place-items-center rounded-md bg-panel font-mono text-[9px] text-faint">Q</span>
                <p className="font-display text-lg font-medium leading-7">{exchange.question}</p>
              </div>

              {exchange.pending ? (
                <PendingState />
              ) : exchange.response ? (
                <div className="rounded-xl border border-line bg-surface p-5 sm:p-6">
                  <div className="max-w-none text-[15px] leading-7 text-fg [&_h2]:mb-4 [&_h2]:mt-7 [&_h2]:font-display [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:tracking-[-0.035em] [&_h2:first-child]:mt-0 [&_h3]:mb-2 [&_h3]:mt-6 [&_h3]:font-display [&_h3]:text-lg [&_h3]:font-semibold [&_li]:ml-5 [&_li]:list-disc [&_li]:py-0.5 [&_p]:my-3 [&_strong]:text-fg">
                    <ReactMarkdown>{exchange.response.answer}</ReactMarkdown>
                  </div>
                  <Citations response={exchange.response} />
                </div>
              ) : exchange.failed ? (
                <div className="rounded-xl border border-line bg-surface p-5">
                  <p className="text-sm font-medium text-fg">The answer took too long.</p>
                  <p className="mt-2 text-sm leading-6 text-muted">
                    Retrieval was interrupted. Your question is safe to retry.
                  </p>
                  <button
                    className="mt-4 rounded-md border border-line px-3 py-2 text-xs font-medium text-muted transition-colors hover:border-ember hover:text-ember"
                    onClick={() => void ask(exchange.question)}
                    type="button"
                  >
                    Retry question
                  </button>
                </div>
              ) : null}
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      <form
        className="sticky bottom-4 mt-10"
        onSubmit={(event) => {
          event.preventDefault();
          void ask(input);
        }}
      >
        <div className="flex gap-2 rounded-xl border border-line bg-surface p-2">
          <input
            aria-label="Question"
            className="w-full bg-transparent px-3 py-2 text-sm placeholder:text-faint focus:outline-none"
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about markets, pain, or what to build…"
            value={input}
          />
          <button
            className="editorial-button shrink-0 py-2 disabled:translate-y-0 disabled:opacity-40"
            disabled={busy || input.trim().length < 3}
            type="submit"
          >
            {busy ? "Working" : "Ask"}
          </button>
        </div>
      </form>
    </div>
  );
}

function PendingState() {
  return (
    <div aria-live="polite" className="rounded-xl border border-line bg-surface p-5">
      <div className="flex items-center gap-3">
        <span className="flex gap-1" aria-hidden="true">
          {[0, 1, 2].map((dot) => (
            <span
              className="h-1.5 w-1.5 animate-pulse rounded-full bg-ember"
              key={dot}
              style={{ animationDelay: `${dot * 180}ms` }}
            />
          ))}
        </span>
        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
          Retrieving and checking evidence
        </p>
      </div>
    </div>
  );
}

function Citations({ response }: { response: ChatResponse }) {
  if (response.cited_posts.length === 0 && response.cited_opportunities.length === 0) {
    return null;
  }
  return (
    <div className="mt-6 border-t border-line pt-5">
      <p className="mb-3 font-mono text-[9px] uppercase tracking-[0.14em] text-faint">
        Source evidence
      </p>
      {response.cited_opportunities.map((opportunity) => (
        <Link
          className="block rounded-md px-2 py-2 font-mono text-[11px] text-faint transition-colors hover:bg-panel hover:text-ember"
          href={`/opportunities/${opportunity.slug}`}
          key={opportunity.id}
        >
          ◆ {opportunity.title}
        </Link>
      ))}
      {response.cited_posts.map((post) => (
        <a
          className="block rounded-md px-2 py-2 font-mono text-[11px] text-faint transition-colors hover:bg-panel hover:text-ember"
          href={post.url}
          key={post.id}
          rel="noreferrer"
          target="_blank"
        >
          → {post.title ?? "post"} · {SOURCE_LABELS[post.source] ?? post.source}
        </a>
      ))}
    </div>
  );
}
