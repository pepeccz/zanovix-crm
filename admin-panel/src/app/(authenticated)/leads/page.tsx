"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { UserCheck } from "lucide-react";
import { sileo } from "sileo";
import api from "@/lib/api";
import type { Lead, LeadStatus, LeadVertical, LeadChannel } from "@/lib/types";
import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { PaginationControls } from "@/components/shared/pagination-controls";
import { NewLeadDialog } from "@/components/shared/new-lead-dialog";
import { ConvertLeadDialog } from "@/components/shared/convert-lead-dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const LIMIT = 50;

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

const VERTICAL_LABELS: Record<LeadVertical, string> = {
  clinicas_dentales: "Clínicas Dentales",
  general: "General",
};

const CHANNEL_LABELS: Record<LeadChannel, string> = {
  email_marketing: "Email Marketing",
  cold_calling: "Cold Calling",
  networking: "Networking",
  referral: "Referido",
  web_form: "Formulario Web",
  other: "Otro",
};

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function LeadsPage() {
  const t = useTranslations("page.leads");
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [offset, setOffset] = useState(0);

  // Filters
  const [vertical, setVertical] = useState<string>("all");
  const [channel, setChannel] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");

  const fetchLeads = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.listLeads({
        vertical: vertical !== "all" ? vertical : undefined,
        channel: channel !== "all" ? channel : undefined,
        status: status !== "all" ? status : undefined,
        limit: LIMIT,
        offset,
      });
      setLeads(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error("Error fetching leads:", error);
      sileo.error({ title: "Error al cargar los leads" });
    } finally {
      setIsLoading(false);
    }
  }, [vertical, channel, status, offset]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  // Reset offset when filters change
  const handleFilterChange = (setter: (v: string) => void) => (v: string) => {
    setter(v);
    setOffset(0);
  };

  return (
    <PageContainer>
      <PageHeader
        title={t("title")}
        description={t("lede")}
        right={<NewLeadDialog onSuccess={fetchLeads} />}
      />

      <Card>
        <CardHeader className="pb-4">
          {/* Filter bar */}
          <div className="flex flex-wrap gap-3">
            <Select
              value={vertical}
              onValueChange={handleFilterChange(setVertical)}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Vertical" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los verticales</SelectItem>
                <SelectItem value="clinicas_dentales">Clínicas Dentales</SelectItem>
                <SelectItem value="general">General</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={channel}
              onValueChange={handleFilterChange(setChannel)}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Canal" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los canales</SelectItem>
                <SelectItem value="email_marketing">Email Marketing</SelectItem>
                <SelectItem value="cold_calling">Cold Calling</SelectItem>
                <SelectItem value="networking">Networking</SelectItem>
                <SelectItem value="referral">Referido</SelectItem>
                <SelectItem value="web_form">Formulario Web</SelectItem>
                <SelectItem value="other">Otro</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={status}
              onValueChange={handleFilterChange(setStatus)}
            >
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los estados</SelectItem>
                <SelectItem value="new">Nuevo</SelectItem>
                <SelectItem value="contacted">Contactado</SelectItem>
                <SelectItem value="qualified">Calificado</SelectItem>
                <SelectItem value="disqualified">Descartado</SelectItem>
                <SelectItem value="converted">Convertido</SelectItem>
              </SelectContent>
            </Select>

            {(vertical !== "all" || channel !== "all" || status !== "all") && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setVertical("all");
                  setChannel("all");
                  setStatus("all");
                  setOffset(0);
                }}
              >
                Limpiar filtros
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-pulse text-muted-foreground">
                Cargando leads...
              </div>
            </div>
          ) : leads.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <UserCheck className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">
                {vertical !== "all" || channel !== "all" || status !== "all"
                  ? "No se encontraron leads con esos filtros"
                  : "Aún no hay leads capturados"}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Vertical</TableHead>
                    <TableHead>Canal</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Propietario</TableHead>
                    <TableHead className="w-[160px]">Acción</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leads.map((lead) => (
                    <TableRow
                      key={lead.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => router.push(`/leads/${lead.id}`)}
                    >
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDate(lead.created_at)}
                      </TableCell>
                      <TableCell className="font-medium">{lead.name}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {lead.email}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {VERTICAL_LABELS[lead.vertical] ?? lead.vertical}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {CHANNEL_LABELS[lead.channel] ?? lead.channel}
                      </TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANTS[lead.status]}>
                          {STATUS_LABELS[lead.status] ?? lead.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {lead.owner_id ? (
                          <span className="font-mono text-[10px]">
                            {lead.owner_id.slice(0, 8)}…
                          </span>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => router.push(`/leads/${lead.id}`)}
                          >
                            Ver
                          </Button>
                          {lead.status === "qualified" ? (
                            <ConvertLeadDialog
                              lead={lead}
                              onSuccess={fetchLeads}
                            />
                          ) : (
                            <TooltipProvider delayDuration={150}>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      disabled
                                    >
                                      Convertir
                                    </Button>
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent>
                                  Solo se pueden convertir leads calificados.
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {total > LIMIT && (
            <PaginationControls
              total={total}
              limit={LIMIT}
              offset={offset}
              onPageChange={setOffset}
              className="mt-4"
            />
          )}
        </CardContent>
      </Card>
    </PageContainer>
  );
}
