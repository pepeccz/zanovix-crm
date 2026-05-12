"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import api from "@/lib/api";
import type { Ticket, TicketStatus, TicketPriority } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { sileo } from "sileo";
import { Plus } from "lucide-react";

const STATUS_FILTERS: (TicketStatus | "all")[] = [
  "all",
  "pending",
  "in_progress",
  "closed",
];

function TicketStatusBadge({ status }: { status: TicketStatus }) {
  const config: Record<TicketStatus, { label: string; classes: string }> = {
    pending: {
      label: "Pendiente",
      classes: "bg-amber-50 text-amber-700 border-amber-300",
    },
    in_progress: {
      label: "En curso",
      classes: "bg-blue-50 text-blue-700 border-blue-300",
    },
    closed: {
      label: "Cerrado",
      classes: "bg-zx-paper-2 text-zx-ink-mute border-zx-rule",
    },
  };
  const { label, classes } = config[status];
  return (
    <span
      className={`inline-block rounded-sm border px-2 py-0.5 text-[11px] uppercase tracking-wide ${classes}`}
    >
      {label}
    </span>
  );
}

function TicketPriorityChip({ priority }: { priority: TicketPriority }) {
  const config: Record<TicketPriority, { label: string; classes: string }> = {
    high: { label: "Alta", classes: "text-red-700" },
    medium: { label: "Media", classes: "text-amber-700" },
    low: { label: "Baja", classes: "text-zx-ink-mute" },
  };
  const { label, classes } = config[priority];
  return (
    <span className={`text-[11px] font-semibold uppercase tracking-wide ${classes}`}>
      {label}
    </span>
  );
}

function NewTicketDialog({ onSuccess }: { onSuccess: () => void }) {
  const t = useTranslations();
  const [open, setOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("medium");
  const [body, setBody] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setIsSaving(true);
    try {
      await api.me.postMyTicket({ title: title.trim(), priority });
      sileo.success({ title: "Ticket creado" });
      setOpen(false);
      setTitle("");
      setPriority("medium");
      setBody("");
      onSuccess();
    } catch {
      sileo.error({ title: t("dialog.newTicket.error") });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-zx-green text-zx-paper hover:bg-zx-green/90">
          <Plus className="h-4 w-4 mr-1.5" />
          {t("page.client.support.newTicket")}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("dialog.newTicket.title")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <div className="space-y-1.5">
            <Label htmlFor="ticket-title">
              {t("dialog.newTicket.fields.title")}
            </Label>
            <Input
              id="ticket-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              disabled={isSaving}
            />
          </div>
          <div className="space-y-1.5">
            <Label>{t("dialog.newTicket.fields.priority")}</Label>
            <div className="flex gap-3">
              {(["high", "medium", "low"] as TicketPriority[]).map((p) => (
                <label
                  key={p}
                  className="flex cursor-pointer items-center gap-2 text-[13px]"
                >
                  <input
                    type="radio"
                    name="priority"
                    value={p}
                    checked={priority === p}
                    onChange={() => setPriority(p)}
                    disabled={isSaving}
                    className="accent-zx-green"
                  />
                  {p === "high" ? "Alta" : p === "medium" ? "Media" : "Baja"}
                </label>
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ticket-body">
              {t("dialog.newTicket.fields.body")}
            </Label>
            <Textarea
              id="ticket-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={4}
              disabled={isSaving}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={isSaving}
            >
              {t("dialog.newTicket.cancel")}
            </Button>
            <Button
              type="submit"
              disabled={isSaving || !title.trim()}
              className="bg-zx-green text-zx-paper hover:bg-zx-green/90"
            >
              {isSaving ? "Enviando…" : t("dialog.newTicket.submit")}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function SupportPage() {
  const t = useTranslations();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [filter, setFilter] = useState<TicketStatus | "all">("all");
  const [isLoading, setIsLoading] = useState(true);

  const fetchTickets = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.me.getMyTickets(
        filter === "all" ? undefined : filter
      );
      setTickets(data.items);
    } catch {
      sileo.error({ title: "Error al cargar los tickets" });
    } finally {
      setIsLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  const filterLabels: Record<TicketStatus | "all", string> = {
    all: t("page.client.support.filter.all"),
    pending: t("page.client.support.filter.pending"),
    in_progress: t("page.client.support.filter.in_progress"),
    closed: t("page.client.support.filter.closed"),
  };

  return (
    <div className="-m-10">
      <header className="border-b border-zx-rule px-10 py-8">
        <div className="flex items-start justify-between">
          <div>
            <p className="font-serif italic text-[14px] text-zx-green mb-2">
              — {t("page.client.support.eyebrow")}
            </p>
            <h1 className="font-serif text-5xl font-light tracking-tight text-zx-ink leading-tight max-w-3xl mb-3">
              {t("page.client.support.title")}
            </h1>
            <p className="font-serif italic text-[18px] text-zx-ink-mute max-w-2xl">
              {t("page.client.support.lede")}
            </p>
          </div>
          <NewTicketDialog onSuccess={fetchTickets} />
        </div>
      </header>

      {/* Filter chips */}
      <div className="flex gap-2 border-b border-zx-rule px-10 py-3">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-full px-3 py-1 text-[12px] font-medium transition-colors ${
              filter === f
                ? "bg-zx-ink text-zx-paper"
                : "bg-zx-paper-2 text-zx-ink-soft hover:bg-zx-rule"
            }`}
          >
            {filterLabels[f]}
          </button>
        ))}
      </div>

      {/* Ticket list */}
      <div className="px-10 py-6">
        {isLoading ? (
          <div className="flex h-32 items-center justify-center">
            <div className="animate-pulse text-zx-ink-mute">Cargando...</div>
          </div>
        ) : tickets.length === 0 ? (
          <p className="font-serif italic text-zx-ink-mute">
            {t("page.client.support.empty")}
          </p>
        ) : (
          tickets.map((ticket) => (
            <div
              key={ticket.id}
              className="flex items-start justify-between border-b border-zx-rule py-5 gap-4"
            >
              <div className="flex-1">
                <p className="font-serif text-[17px] text-zx-ink leading-snug mb-2">
                  {ticket.title}
                </p>
                <div className="flex items-center gap-3">
                  <TicketStatusBadge status={ticket.status} />
                  <TicketPriorityChip priority={ticket.priority} />
                  <span className="text-[11px] text-zx-ink-mute">
                    {new Date(ticket.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
