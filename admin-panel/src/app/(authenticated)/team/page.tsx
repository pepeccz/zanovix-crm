"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Users } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { sileo } from "sileo";
import api from "@/lib/api";
import type { AssignableUser, ClientListResponse, ServiceListResponse } from "@/lib/types";
import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";

// ─── helpers ────────────────────────────────────────────────────────────────

/** Returns initials from a display_name or falls back to first letter of email */
function initials(user: AssignableUser): string {
  const name = user.display_name ?? user.email;
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

/** Avatar circle with initials — same size pattern used across pipeline cards */
function UserAvatar({ user, size = 42 }: { user: AssignableUser; size?: number }) {
  const init = initials(user);
  const sizeClass = size === 42 ? "h-[42px] w-[42px] text-[15px]" : "h-9 w-9 text-[13px]";
  return (
    <div
      className={`${sizeClass} flex shrink-0 items-center justify-center rounded-full bg-zx-green/15 font-semibold text-zx-green select-none`}
      aria-label={user.display_name ?? user.email}
    >
      {init}
    </div>
  );
}

const ROLE_LABEL_KEY: Record<string, string> = {
  admin: "page.team.role.admin",
  consultor: "page.team.role.consultor",
  comercial: "page.team.role.comercial",
};

// ─── member row ─────────────────────────────────────────────────────────────

interface TeamMemberRowProps {
  user: AssignableUser;
  clientsCount: number;
  servicesCount: number;
}

function TeamMemberRow({ user, clientsCount, servicesCount }: TeamMemberRowProps) {
  const t = useTranslations();
  const roleKey = ROLE_LABEL_KEY[user.role] ?? "page.team.role.consultor";

  return (
    <div
      className="grid items-center gap-6 border-b border-zx-rule px-10 py-5"
      style={{ gridTemplateColumns: "1fr 160px 160px 160px" }}
    >
      {/* Identity */}
      <div className="flex items-center gap-4 min-w-0">
        <UserAvatar user={user} />
        <div className="min-w-0">
          <div className="font-serif text-[17px] text-zx-ink leading-snug truncate">
            {user.display_name ?? user.email}
          </div>
          <div className="mt-0.5 text-[11.5px] tracking-[0.04em] text-zx-ink-mute">
            {t(roleKey)}
          </div>
        </div>
      </div>

      {/* Clients metric */}
      <div>
        <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-zx-ink-mute">
          {t("page.team.metric.clients")}
        </div>
        <div className="font-serif text-[22px] font-normal tracking-[-0.01em] text-zx-ink">
          {clientsCount}
        </div>
      </div>

      {/* Services metric */}
      <div>
        <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-zx-ink-mute">
          {t("page.team.metric.services")}
        </div>
        <div className="font-serif text-[22px] font-normal tracking-[-0.01em] text-zx-ink">
          {servicesCount}
        </div>
      </div>

      {/* Load placeholder */}
      <div>
        <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-zx-ink-mute">
          {t("page.team.metric.load")}
        </div>
        <div
          className="font-serif text-[22px] font-normal text-zx-ink-mute"
          title={t("page.team.metric.loadPlaceholder")}
        >
          —
        </div>
      </div>
    </div>
  );
}

// ─── skeleton ────────────────────────────────────────────────────────────────

function TeamSkeleton() {
  return (
    <div>
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="grid items-center gap-6 border-b border-zx-rule px-10 py-5"
          style={{ gridTemplateColumns: "1fr 160px 160px 160px" }}
        >
          <div className="flex items-center gap-4">
            <Skeleton className="h-[42px] w-[42px] rounded-full" />
            <div className="space-y-1.5">
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
          <Skeleton className="h-7 w-10" />
          <Skeleton className="h-7 w-10" />
          <Skeleton className="h-5 w-5" />
        </div>
      ))}
    </div>
  );
}

// ─── page ────────────────────────────────────────────────────────────────────

interface MemberStats {
  user: AssignableUser;
  clientsCount: number;
  servicesCount: number;
}

export default function TeamPage() {
  const t = useTranslations();

  const [members, setMembers] = useState<MemberStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTeam = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Fetch user list
      const usersResp = await api.listUsers();
      const users = usersResp.items;

      if (users.length === 0) {
        setMembers([]);
        return;
      }

      // 2. For each user fetch clients count + services count (N+1 accepted for N < 10)
      const statsPromises = users.map(async (user) => {
        const [clientsResp, servicesResp] = await Promise.allSettled([
          api.getClients({ owner_id: user.id, limit: 1 }) as Promise<ClientListResponse>,
          api.getServices({ owner_id: user.id, limit: 1 }) as Promise<ServiceListResponse>,
        ]);
        const clientsCount =
          clientsResp.status === "fulfilled" ? clientsResp.value.total : 0;
        const servicesCount =
          servicesResp.status === "fulfilled" ? servicesResp.value.total : 0;
        return { user, clientsCount, servicesCount };
      });

      const stats = await Promise.all(statsPromises);
      setMembers(stats);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error desconocido";
      setError(msg);
      sileo.error({ title: "No se pudo cargar el equipo", description: msg });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTeam();
  }, [fetchTeam]);

  return (
    <PageContainer>
      <PageHeader
        eyebrow={t("page.team.eyebrow")}
        title={t("page.team.title")}
        lede={t("page.team.lede")}
      />

      {isLoading && <TeamSkeleton />}

      {!isLoading && error && (
        <div className="px-10 py-16 text-center">
          <Users className="mx-auto mb-3 h-10 w-10 text-zx-ink-mute" />
          <p className="font-serif italic text-zx-ink-mute">{error}</p>
        </div>
      )}

      {!isLoading && !error && members.length === 0 && (
        <div className="px-10 py-16 text-center">
          <Users className="mx-auto mb-3 h-10 w-10 text-zx-ink-mute" />
          <p className="font-serif text-lg text-zx-ink">
            {t("page.team.empty.title")}
          </p>
          <p className="mt-1 font-serif italic text-zx-ink-mute">
            {t("page.team.empty.description")}
          </p>
        </div>
      )}

      {!isLoading && !error && members.length > 0 && (
        <div>
          {members.map(({ user, clientsCount, servicesCount }) => (
            <TeamMemberRow
              key={user.id}
              user={user}
              clientsCount={clientsCount}
              servicesCount={servicesCount}
            />
          ))}
        </div>
      )}
    </PageContainer>
  );
}
