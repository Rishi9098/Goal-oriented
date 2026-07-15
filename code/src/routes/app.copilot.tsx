import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { motion } from "motion/react";
import { Send, Sparkles } from "lucide-react";
import { auth, api } from "@/lib/api";
import { findLifeEventType } from "@/lib/life-events";

export const Route = createFileRoute("/app/copilot")({
  head: () => ({ meta: [{ title: "AI Copilot — Northstar" }] }),
  staticData: { shellTitle: "AI Copilot" },
  component: Copilot,
});

type Msg = { role: "user" | "assistant"; content: string };

const SUGGESTIONS = [
  "Explain my Plan Health score",
  "Review my goal probabilities",
  "How can I improve my savings rate?",
  "What's my retirement outlook?",
  "Should I adjust my risk profile?",
];

function Copilot() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [convId, setConvId] = useState<string | undefined>(undefined);
  const [recentEventPrompt, setRecentEventPrompt] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // LifeEventIntegrationReview.md Phase 2 — an honest, smarter suggested
  // prompt when the user has recorded something recently. This is a
  // *suggestion* the user still chooses to send, not a claim that the model
  // was secretly given extra context: clicking it sends this literal
  // question through the exact same, unmodified api.chat call as every
  // other suggestion below.
  useEffect(() => {
    api
      .getLifeEvents({ limit: 1 })
      .then((result) => {
        const latest = result.items[0];
        if (!latest) return;
        const label = findLifeEventType(latest.event_type)?.label ?? latest.event_type;
        setRecentEventPrompt(`How did recording my ${label} affect my plan?`);
      })
      .catch(() => setRecentEventPrompt(null));
  }, []);

  useEffect(() => {
    auth
      .me()
      .then((user) => {
        const firstName = (user.full_name ?? user.email ?? "").trim().split(/\s+/)[0];
        setMessages([
          {
            role: "assistant",
            content: `Hi ${firstName} — I'm your AI financial planner. Ask me anything about your goals, projections, or investment strategy.`,
          },
        ]);
      })
      .catch(() => {
        setMessages([
          {
            role: "assistant",
            content:
              "Hi — I'm your AI financial planner. Ask me anything about your goals, projections, or investment strategy.",
          },
        ]);
      });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  const send = async (text: string) => {
    if (!text.trim() || thinking) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setThinking(true);
    try {
      const result = await api.chat(text, convId);
      setConvId(result.conversation_id);
      setMessages((m) => [...m, { role: "assistant", content: result.reply }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Sorry, I couldn't process that. Please try again." },
      ]);
    } finally {
      setThinking(false);
    }
  };

  return (
    <div className="grid lg:grid-cols-[1fr_320px] gap-6">
      <div className="surface-card flex flex-col h-[calc(100vh-12rem)]">
        <div className="px-5 py-4 border-b border-border flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-cyan" />
          <p className="font-display">Copilot</p>
          <span className="ml-auto text-xs text-muted-foreground">Powered by AI</span>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                  m.role === "user"
                    ? "bg-gradient-to-br from-primary to-cyan text-primary-foreground"
                    : "bg-surface border border-border"
                }`}
              >
                {m.content}
              </div>
            </motion.div>
          ))}
          {thinking && (
            <div className="flex gap-1.5 text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-cyan animate-pulse" />
              <span className="h-2 w-2 rounded-full bg-cyan animate-pulse [animation-delay:120ms]" />
              <span className="h-2 w-2 rounded-full bg-cyan animate-pulse [animation-delay:240ms]" />
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="border-t border-border p-3 flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about your plan…"
            className="flex-1 rounded-lg border border-border bg-surface px-3 py-2.5 text-sm outline-none focus:border-primary"
          />
          <button
            type="submit"
            disabled={thinking}
            className="rounded-lg bg-gradient-to-r from-primary to-cyan px-4 text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>

      <div className="space-y-3">
        {recentEventPrompt && (
          <>
            <p className="text-xs uppercase tracking-widest text-muted-foreground">
              Based on your recent activity
            </p>
            <button
              onClick={() => send(recentEventPrompt)}
              disabled={thinking}
              className="w-full text-left surface-card p-4 text-sm border-primary/30 hover:border-primary/60 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {recentEventPrompt}
            </button>
          </>
        )}
        <p className="text-xs uppercase tracking-widest text-muted-foreground">Suggested prompts</p>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => send(s)}
            disabled={thinking}
            className="w-full text-left surface-card p-4 text-sm hover:border-border-strong transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
