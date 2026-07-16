import type {
  WorkflowAction,
  WorkflowConditionLeaf,
} from "@/lib/api";

export type WorkflowSelection =
  | { kind: "trigger" }
  | { kind: "conditions" }
  | { kind: "action"; actionId: string }
  | null;

export type WorkflowBuilderActions = {
  select: (selection: WorkflowSelection) => void;
  setTriggerType: (type: string) => void;
  setConditionsOp: (op: "and" | "or") => void;
  addConditionRule: () => void;
  updateConditionRule: (index: number, patch: Partial<WorkflowConditionLeaf>) => void;
  removeConditionRule: (index: number) => void;
  addAction: (type: string) => void;
  updateAction: (
    actionId: string,
    patch: Partial<Pick<WorkflowAction, "name" | "type">>,
  ) => void;
  updateActionConfig: (actionId: string, config: Record<string, unknown>) => void;
  removeAction: (actionId: string) => void;
  moveAction: (actionId: string, dir: -1 | 1) => void;
  setSetting: (key: string, value: unknown) => void;
};
