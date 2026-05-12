"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/auth-context";
import api from "@/lib/api";
import type { Message } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { sileo } from "sileo";
import { Send } from "lucide-react";

const POLL_INTERVAL_MS = 10_000;

function groupByDay(messages: Message[]): [string, Message[]][] {
  const groups = new Map<string, Message[]>();
  for (const m of messages) {
    const day = m.created_at.slice(0, 10); // YYYY-MM-DD
    if (!groups.has(day)) groups.set(day, []);
    groups.get(day)!.push(m);
  }
  return Array.from(groups.entries());
}

export default function ChatPage() {
  const t = useTranslations();
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [body, setBody] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const sinceRef = useRef<string | undefined>(undefined);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadMessages = useCallback(async (initial = false) => {
    if (document.visibilityState !== "visible" && !initial) return;
    try {
      if (initial) setIsLoading(true);
      const data = await api.me.getMyMessages(
        initial ? undefined : sinceRef.current
      );
      if (data.items.length > 0) {
        if (initial) {
          setMessages(data.items);
        } else {
          setMessages((prev) => [...prev, ...data.items]);
        }
        // Track the latest timestamp for polling
        const latest = data.items[data.items.length - 1].created_at;
        sinceRef.current = latest;
      }
    } catch {
      if (initial) sileo.error({ title: "Error al cargar mensajes" });
    } finally {
      if (initial) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMessages(true);

    const interval = setInterval(() => {
      if (document.visibilityState === "visible") {
        loadMessages(false);
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [loadMessages]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const trimmed = body.trim();
    if (!trimmed) return;
    setIsSending(true);
    try {
      const sent = await api.me.postMyMessage({ body: trimmed });
      setMessages((prev) => [...prev, sent]);
      sinceRef.current = sent.created_at;
      setBody("");
    } catch {
      sileo.error({ title: "Error al enviar el mensaje" });
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const grouped = groupByDay(messages);

  const isOwnMessage = (m: Message) =>
    m.sender_contact_id !== null || m.sender_user_id === null;

  return (
    <div className="-m-10 flex h-full flex-col">
      <header className="border-b border-zx-rule px-10 py-6 shrink-0">
        <p className="font-serif italic text-[14px] text-zx-green mb-1">
          — {t("page.client.chat.eyebrow")}
        </p>
        <h1 className="font-serif text-3xl font-light tracking-tight text-zx-ink">
          {t("page.client.chat.title")}
        </h1>
        <p className="mt-1 font-serif italic text-[14px] text-zx-ink-mute">
          {t("page.client.chat.lede")}
        </p>
      </header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-10 py-6 space-y-1">
        {isLoading ? (
          <div className="flex h-32 items-center justify-center">
            <div className="animate-pulse text-zx-ink-mute">Cargando...</div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-32 items-center justify-center">
            <p className="font-serif italic text-zx-ink-mute">
              {t("page.client.chat.empty")}
            </p>
          </div>
        ) : (
          grouped.map(([day, msgs]) => (
            <div key={day}>
              {/* Day divider */}
              <div className="flex items-center gap-3 py-4">
                <div className="h-px flex-1 bg-zx-rule" />
                <span className="text-[11px] uppercase tracking-[0.12em] text-zx-ink-mute">
                  {day === new Date().toISOString().slice(0, 10)
                    ? t("page.client.chat.today")
                    : new Date(day).toLocaleDateString()}
                </span>
                <div className="h-px flex-1 bg-zx-rule" />
              </div>
              {/* Messages */}
              {msgs.map((m) => {
                const own = isOwnMessage(m);
                return (
                  <div
                    key={m.id}
                    className={`flex mb-2 ${own ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[70%] rounded-sm px-4 py-2.5 text-[14px] leading-relaxed ${
                        own
                          ? "bg-zx-night text-zx-paper"
                          : "bg-zx-paper-2 text-zx-ink"
                      }`}
                    >
                      {m.body}
                      <div
                        className={`mt-1 text-[10px] ${
                          own ? "text-zx-paper/50" : "text-zx-ink-mute"
                        }`}
                      >
                        {new Date(m.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <div className="shrink-0 border-t border-zx-rule px-10 py-4">
        <div className="flex gap-3 items-end">
          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t("page.client.chat.placeholder")}
            rows={2}
            className="resize-none flex-1 bg-zx-paper"
            disabled={isSending}
          />
          <Button
            onClick={handleSend}
            disabled={isSending || !body.trim()}
            className="bg-zx-green text-zx-paper hover:bg-zx-green/90 shrink-0"
          >
            <Send className="h-4 w-4" />
            <span className="ml-2">{t("page.client.chat.send")}</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
