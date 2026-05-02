"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowLeft, Loader2, UserCog, ChevronRight } from "lucide-react";
import { sileo } from "sileo";
import api from "@/lib/api";
import type {
  Lead,
  LeadStatus,
  AssignableUser,
} from "@/lib/types";
import { VALID_TRANSITIONS } from "@/lib/types";
import { useAuth } from "@/contexts/auth-context";

// ---------------------------------------------------------------------------
// Status helpers
// ---------------------------------------------------------------------------

const STATUS_LABELS: Record<LeadStatus, string> = {
  new: "Nuevo",
  contacted: "Contactado",
  qualified: "Calificado",
  disqualified: "Descartado",
  converted: "Convertido",
};

const STATUS_VARIANTS: Record<
  LeadStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  new: "secondary",
  contacted: "outline",
  qualified: "default",
  disqualified: "destructive",
  converted: "default",
};

const VERTICAL_LABELS: Record<string, string> = {
  clinicas_dentales: "Clínicas Dentales",
  general: "General",
};

const CHANNEL_LABELS: Record<string, string> = {
  email_marketing: "Email Marketing",
  cold_calling: "Cold Calling",
  networking: "Networking",
  referral: "Referido",
  web_form: "Formulario Web",
  other: "Otro",
};

function formatDateTime(dateStr: string) {
  return new Date(dateStr).toLocaleString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ---------------------------------------------------------------------------
// AssignModal
// ---------------------------------------------------------------------------

function AssignModal({
  open,
  onClose,
  onAssign,
}: {
  open: boolean;
  onClose: () => void;
  onAssign: (userId: string) => Promise<void>;
}) {
  const [users, setUsers] = useState<AssignableUser[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setIsLoading(true);
    api
      .listUsers()
      .then((data) => setUsers(data.items))
      .catch(() => sileo.error({ title: "Error al cargar usuarios" }))
      .finally(() => setIsLoading(false));
  }, [open]);

  async function handleConfirm() {
    if (!selected) return;
    setIsSaving(true);
    try {
      await onAssign(selected);
      onClose();
    } finally {
      setIsSaving(false);
    }
  }

  const isEmpty = !isLoading && users.length === 0;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>Asignar propietario</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : isEmpty ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            Gestión de usuarios disponible próximamente
          </p>
        ) : (
          <div className="space-y-4 py-2">
            <Select value={selected} onValueChange={setSelected}>
              <SelectTrigger>
                <SelectValue placeholder="Seleccionar usuario..." />
              </SelectTrigger>
              <SelectContent>
                {users.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.display_name || u.email} ({u.role})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={onClose} disabled={isSaving}>
                Cancelar
              </Button>
              <Button
                onClick={handleConfirm}
                disabled={!selected || isSaving}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Asignando...
                  </>
                ) : (
                  "Asignar"
                )}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const leadId = params.id as string;

  const [lead, setLead] = useState<Lead | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [showRawPayload, setShowRawPayload] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);

  const fetchLead = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.getLead(leadId);
      setLead(data);
    } catch (error) {
      console.error("Error fetching lead:", error);
      sileo.error({ title: "Error al cargar el lead" });
    } finally {
      setIsLoading(false);
    }
  }, [leadId]);

  useEffect(() => {
    fetchLead();
  }, [fetchLead]);

  async function handleTransition(newStatus: LeadStatus) {
    if (!lead) return;
    setIsTransitioning(true);
    try {
      const updated = await api.updateLeadStatus(leadId, newStatus);
      setLead(updated);
      sileo.success({
        title: `Estado actualizado a "${STATUS_LABELS[newStatus]}"`,
      });
    } catch (error) {
      sileo.error({
        title: "Error al actualizar estado",
        description: error instanceof Error ? error.message : undefined,
      });
    } finally {
      setIsTransitioning(false);
    }
  }

  async function handleAssign(ownerId: string) {
    const updated = await api.assignLead(leadId, ownerId);
    setLead(updated);
    sileo.success({ title: "Lead asignado correctamente" });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <p className="text-muted-foreground">Lead no encontrado</p>
        <Button variant="outline" onClick={() => router.push("/leads")}>
          Volver a Leads
        </Button>
      </div>
    );
  }

  const validNext = VALID_TRANSITIONS[lead.status as LeadStatus] ?? [];
  const isAdmin = user?.role === "admin";

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => router.back()}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold truncate">{lead.name}</h1>
              <Badge variant={STATUS_VARIANTS[lead.status as LeadStatus]}>
                {STATUS_LABELS[lead.status as LeadStatus] ?? lead.status}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {lead.email} · Creado {formatDateTime(lead.created_at)}
            </p>
          </div>
        </div>

        {/* Admin-only assign button */}
        {isAdmin && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowAssignModal(true)}
            className="shrink-0"
          >
            <UserCog className="h-4 w-4 mr-2" />
            Asignar a...
          </Button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Contact info */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Información de contacto
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <span className="text-muted-foreground">Nombre</span>
              <span className="font-medium">{lead.name}</span>

              <span className="text-muted-foreground">Email</span>
              <span>{lead.email}</span>

              <span className="text-muted-foreground">Teléfono</span>
              <span>{lead.phone || "—"}</span>

              <span className="text-muted-foreground">Empresa</span>
              <span>{lead.company || "—"}</span>

              <span className="text-muted-foreground">URL origen</span>
              <span className="truncate">
                {lead.source_url ? (
                  <a
                    href={lead.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {lead.source_url}
                  </a>
                ) : (
                  "—"
                )}
              </span>

              <span className="text-muted-foreground">Notas</span>
              <span className="whitespace-pre-wrap">{lead.notes || "—"}</span>
            </div>
          </CardContent>
        </Card>

        {/* Metadata + status transitions */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                Metadata
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                <span className="text-muted-foreground">Vertical</span>
                <Badge variant="outline" className="w-fit">
                  {VERTICAL_LABELS[lead.vertical] ?? lead.vertical}
                </Badge>

                <span className="text-muted-foreground">Canal</span>
                <span>{CHANNEL_LABELS[lead.channel] ?? lead.channel}</span>

                <span className="text-muted-foreground">Propietario</span>
                <span className="font-mono text-xs">
                  {lead.owner_id ? lead.owner_id.slice(0, 12) + "…" : "—"}
                </span>

                <span className="text-muted-foreground">Actualizado</span>
                <span className="text-xs">
                  {formatDateTime(lead.updated_at)}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Status transitions */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                Cambiar estado
              </CardTitle>
            </CardHeader>
            <CardContent>
              {validNext.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Estado terminal — no hay transiciones disponibles
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {validNext.map((nextStatus) => (
                    <Button
                      key={nextStatus}
                      variant="outline"
                      size="sm"
                      disabled={isTransitioning}
                      onClick={() => handleTransition(nextStatus)}
                    >
                      {isTransitioning ? (
                        <Loader2 className="h-3 w-3 animate-spin mr-1" />
                      ) : (
                        <ChevronRight className="h-3 w-3 mr-1" />
                      )}
                      {STATUS_LABELS[nextStatus]}
                    </Button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Raw payload viewer */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Payload original
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowRawPayload((v) => !v)}
            >
              {showRawPayload ? "Ocultar" : "Mostrar"}
            </Button>
          </div>
        </CardHeader>
        {showRawPayload && (
          <CardContent>
            <Separator className="mb-4" />
            <pre className="text-xs bg-muted rounded p-4 overflow-x-auto whitespace-pre-wrap break-all">
              {JSON.stringify(lead, null, 2)}
            </pre>
          </CardContent>
        )}
      </Card>

      {/* Assign modal */}
      {isAdmin && (
        <AssignModal
          open={showAssignModal}
          onClose={() => setShowAssignModal(false)}
          onAssign={handleAssign}
        />
      )}
    </div>
  );
}
