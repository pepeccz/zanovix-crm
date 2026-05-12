"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Star } from "lucide-react";
import { sileo } from "sileo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import api from "@/lib/api";
import type { BillingProfile } from "@/lib/types";
import { BillingProfileDialog } from "./BillingProfileDialog";

interface BillingProfileListProps {
  clientId: string;
  profiles: BillingProfile[];
  onMutate: () => void;
}

export function BillingProfileList({
  clientId,
  profiles,
  onMutate,
}: BillingProfileListProps) {
  const t = useTranslations("page.client_detail.billing");
  const [editingProfile, setEditingProfile] = useState<BillingProfile | null>(
    null
  );
  const [editDialogOpen, setEditDialogOpen] = useState(false);

  async function handleSetDefault(id: string) {
    try {
      await api.setDefaultBillingProfile(id);
      onMutate();
    } catch (err) {
      sileo.error({
        title: t("set_default"),
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteBillingProfile(id);
      onMutate();
    } catch (err) {
      sileo.error({
        title: t("delete"),
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  function handleEdit(profile: BillingProfile) {
    setEditingProfile(profile);
    setEditDialogOpen(true);
  }

  if (profiles.length === 0) {
    return (
      <p className="font-serif italic text-sm text-zx-ink-mute">
        {t("empty_state")}
      </p>
    );
  }

  return (
    <>
      <div className="divide-y divide-zx-rule/50">
        {profiles.map((profile) => (
          <div key={profile.id} className="py-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-serif text-[15px] text-zx-ink">
                    {profile.legal_name}
                  </span>
                  {profile.is_default && (
                    <Badge variant="default" className="gap-1 text-[10px]">
                      <Star className="h-2.5 w-2.5" />
                      {t("default_badge")}
                    </Badge>
                  )}
                </div>
                <p className="text-[11.5px] text-zx-ink-soft mt-0.5">
                  {profile.tax_id_type} {profile.tax_id}
                </p>
                <p className="text-[11.5px] text-zx-ink-mute">
                  {profile.address_line1}, {profile.city} {profile.postal_code}
                </p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {!profile.is_default && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs h-7 px-2"
                    onClick={() => handleSetDefault(profile.id)}
                  >
                    {t("set_default")}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs h-7 px-2"
                  onClick={() => handleEdit(profile)}
                >
                  {t("edit")}
                </Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs h-7 px-2 text-destructive hover:text-destructive"
                    >
                      {t("delete")}
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>{profile.legal_name}</AlertDialogTitle>
                      <AlertDialogDescription>
                        {t("confirm_delete")}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancelar</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => handleDelete(profile.id)}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        {t("delete")}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>
          </div>
        ))}
      </div>

      {editingProfile && (
        <BillingProfileDialog
          clientId={clientId}
          profile={editingProfile}
          open={editDialogOpen}
          onOpenChange={(open) => {
            setEditDialogOpen(open);
            if (!open) setEditingProfile(null);
          }}
          onSuccess={onMutate}
        />
      )}
    </>
  );
}
