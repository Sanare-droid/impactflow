"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Save, Sparkles, Upload, Zap } from "lucide-react";
import {
  api,
  type WorkflowDefinition,
  type WorkflowDetail,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { StepPalette } from "./StepPalette";
import { WorkflowCanvas } from "./WorkflowCanvas";
import { PropertiesPanel } from "./PropertiesPanel";
import { AiAssistDialog } from "./AiAssistDialog";
import type { WorkflowBuilderActions, WorkflowSelection } from "./builder-types";
import {
  FALLBACK_ACTIONS,
  FALLBACK_OPERATORS,
  FALLBACK_TRIGGERS,
  defaultConfigForType,
  emptyConditions,
  newActionId,
  normalizeDefinitionForClient,
  serializeDefinition,
} from "./definition-utils";

export function WorkflowBuilder({ workflow }: { workflow: WorkflowDetail }) {
  const qc = useQueryClient();
  const [definition, setDefinition] = useState<WorkflowDefinition>(() =>
    normalizeDefinitionForClient(workflow.definition),
  );
  const [selection, setSelection] = useState<WorkflowSelection>({ kind: "trigger" });
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setDefinition(normalizeDefinitionForClient(workflow.definition));
    setSelection({ kind: "trigger" });
  }, [workflow.id]);

  const triggersQuery = useQuery({
    queryKey: ["workflow-triggers"],
    queryFn: () => api.listWorkflowTriggers(),
    staleTime: 5 * 60 * 1000,
  });
  const actionsQuery = useQuery({
    queryKey: ["workflow-actions"],
    queryFn: () => api.listWorkflowActions(),
    staleTime: 5 * 60 * 1000,
  });
  const operatorsQuery = useQuery({
    queryKey: ["workflow-operators"],
    queryFn: () => api.listWorkflowOperators(),
    staleTime: 5 * 60 * 1000,
  });

  const triggers = triggersQuery.data?.triggers?.length
    ? triggersQuery.data.triggers
    : FALLBACK_TRIGGERS;
  const actionCatalog = actionsQuery.data?.actions?.length
    ? actionsQuery.data.actions
    : FALLBACK_ACTIONS;
  const operators = operatorsQuery.data?.operators?.length
    ? operatorsQuery.data.operators
    : FALLBACK_OPERATORS;

  const editable = workflow.status !== "archived";

  const invalidate = () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: ["workflow", workflow.id] }),
      qc.invalidateQueries({ queryKey: ["workflow-versions", workflow.id] }),
      qc.invalidateQueries({ queryKey: ["workflows"] }),
    ]);

  const save = useMutation({
    mutationFn: () =>
      api.updateWorkflow(workflow.id, {
        definition: serializeDefinition(definition),
      }),
    onSuccess: async () => {
      setNotice("Workflow saved as a new version.");
      setError(null);
      await invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const activate = useMutation({
    mutationFn: () => api.activateWorkflow(workflow.id),
    onSuccess: async () => {
      setNotice("Workflow activated.");
      setError(null);
      await invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const importDef = useMutation({
    mutationFn: (imported: WorkflowDefinition) =>
      api.importWorkflowDefinition(workflow.id, imported, "Imported definition"),
    onSuccess: async () => {
      setNotice("Definition imported as a new version.");
      setError(null);
      await invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const exportJson = async () => {
    try {
      const payload = await api.exportWorkflowDefinition(workflow.id);
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${workflow.code}-workflow.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  };

  const handleImportFile = async (file: File) => {
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const importedDefinition: WorkflowDefinition = parsed.definition ?? parsed;
      const normalized = normalizeDefinitionForClient(importedDefinition);
      setDefinition(normalized);
      setSelection({ kind: "trigger" });
      importDef.mutate(serializeDefinition(normalized));
    } catch {
      setError("Could not parse JSON file.");
    }
  };

  const actions: WorkflowBuilderActions = useMemo(
    () => ({
      select: setSelection,
      setTriggerType: (type) =>
        setDefinition((prev) => ({
          ...prev,
          trigger: { ...prev.trigger, type },
        })),
      setConditionsOp: (op) =>
        setDefinition((prev) => ({
          ...prev,
          trigger: {
            ...prev.trigger,
            conditions: {
              op,
              rules: prev.trigger.conditions?.rules ?? [],
            },
          },
        })),
      addConditionRule: () =>
        setDefinition((prev) => {
          const existing = prev.trigger.conditions ?? emptyConditions();
          return {
            ...prev,
            trigger: {
              ...prev.trigger,
              conditions: {
                op: existing.op,
                rules: [...existing.rules, { field: "", cmp: "eq", value: "" }],
              },
            },
          };
        }),
      updateConditionRule: (index, patch) =>
        setDefinition((prev) => {
          const existing = prev.trigger.conditions;
          if (!existing) return prev;
          const rules = existing.rules.map((rule, i) =>
            i === index ? { ...rule, ...patch } : rule,
          );
          return {
            ...prev,
            trigger: { ...prev.trigger, conditions: { ...existing, rules } },
          };
        }),
      removeConditionRule: (index) =>
        setDefinition((prev) => {
          const existing = prev.trigger.conditions;
          if (!existing) return prev;
          const rules = existing.rules.filter((_, i) => i !== index);
          return {
            ...prev,
            trigger: {
              ...prev.trigger,
              conditions: rules.length > 0 ? { ...existing, rules } : null,
            },
          };
        }),
      addAction: (type) => {
        const id = newActionId();
        setDefinition((prev) => ({
          ...prev,
          actions: [
            ...prev.actions,
            {
              id,
              type,
              name: "",
              config: defaultConfigForType(type),
              conditions: null,
            },
          ],
        }));
        setSelection({ kind: "action", actionId: id });
      },
      updateAction: (actionId, patch) =>
        setDefinition((prev) => ({
          ...prev,
          actions: prev.actions.map((a) =>
            a.id === actionId ? { ...a, ...patch } : a,
          ),
        })),
      updateActionConfig: (actionId, config) =>
        setDefinition((prev) => ({
          ...prev,
          actions: prev.actions.map((a) =>
            a.id === actionId ? { ...a, config } : a,
          ),
        })),
      removeAction: (actionId) => {
        setDefinition((prev) => ({
          ...prev,
          actions: prev.actions.filter((a) => a.id !== actionId),
        }));
        setSelection((sel) =>
          sel?.kind === "action" && sel.actionId === actionId ? null : sel,
        );
      },
      moveAction: (actionId, dir) =>
        setDefinition((prev) => {
          const list = [...prev.actions];
          const idx = list.findIndex((a) => a.id === actionId);
          const next = idx + dir;
          if (idx < 0 || next < 0 || next >= list.length) return prev;
          [list[idx], list[next]] = [list[next], list[idx]];
          return { ...prev, actions: list };
        }),
      setSetting: (key, value) =>
        setDefinition((prev) => ({
          ...prev,
          settings: { ...prev.settings, [key]: value },
        })),
    }),
    [],
  );

  const disabled = !editable;

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>Builder</CardTitle>
            <CardDescription>
              {editable
                ? "Edit the flow and save to create the next version."
                : "Archived — this workflow is read-only."}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={disabled}
              onClick={() => setAiOpen(true)}
            >
              <Sparkles className="h-3.5 w-3.5" /> AI Assist
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={exportJson}>
              <Download className="h-3.5 w-3.5" /> Export JSON
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={disabled || importDef.isPending}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-3.5 w-3.5" /> Import JSON
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleImportFile(file);
                e.target.value = "";
              }}
            />
            <Button
              type="button"
              size="sm"
              disabled={disabled || save.isPending}
              onClick={() => save.mutate()}
            >
              <Save className="h-3.5 w-3.5" /> {save.isPending ? "Saving…" : "Save"}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={disabled || activate.isPending}
              onClick={() => activate.mutate()}
            >
              <Zap className="h-3.5 w-3.5" />{" "}
              {activate.isPending ? "Activating…" : "Activate"}
            </Button>
          </div>
        </div>
        {notice && <p className="mt-3 text-sm text-teal-700 dark:text-teal-300">{notice}</p>}
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      </Card>

      <div className="grid gap-4 lg:grid-cols-[240px_1fr_320px]">
        <Card className="h-fit">
          <CardTitle className="text-sm">Palette</CardTitle>
          <CardDescription className="mb-3">
            Set the trigger and add action steps.
          </CardDescription>
          <StepPalette
            triggers={triggers}
            actions={actionCatalog}
            disabled={disabled}
            onSetTrigger={(code) => {
              actions.setTriggerType(code);
              setSelection({ kind: "trigger" });
            }}
            onAddAction={(code) => actions.addAction(code)}
          />
        </Card>

        <Card>
          <CardTitle className="text-sm">Canvas</CardTitle>
          <CardDescription className="mb-3">
            Trigger → conditions → actions.
          </CardDescription>
          <WorkflowCanvas
            definition={definition}
            selection={selection}
            actions={actions}
            triggers={triggers}
            actionCatalog={actionCatalog}
            disabled={disabled}
          />
        </Card>

        <Card className="h-fit">
          <CardTitle className="text-sm">Properties</CardTitle>
          <div className="mt-3">
            <PropertiesPanel
              definition={definition}
              selection={selection}
              actions={actions}
              triggers={triggers}
              actionCatalog={actionCatalog}
              operators={operators}
              disabled={disabled}
            />
          </div>
        </Card>
      </div>

      <AiAssistDialog
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        onApply={(def) => {
          const normalized = normalizeDefinitionForClient(def);
          setDefinition(normalized);
          setSelection({ kind: "trigger" });
          setNotice("AI draft applied. Review and save to persist.");
        }}
      />
    </div>
  );
}
