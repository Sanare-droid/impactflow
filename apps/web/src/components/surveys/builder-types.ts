import type { SurveyField, SurveyPage, SurveySection } from "@/lib/api";

export type BuilderSelection =
  | { kind: "field"; pageId: string; sectionId: string; fieldId: string }
  | { kind: "section"; pageId: string; sectionId: string }
  | { kind: "page"; pageId: string }
  | null;

export type BuilderActions = {
  addPage: () => void;
  updatePage: (pageId: string, patch: Partial<Pick<SurveyPage, "title">>) => void;
  deletePage: (pageId: string) => void;
  movePage: (pageId: string, dir: -1 | 1) => void;
  addSection: (pageId: string) => void;
  updateSection: (
    pageId: string,
    sectionId: string,
    patch: Partial<Pick<SurveySection, "title">>,
  ) => void;
  deleteSection: (pageId: string, sectionId: string) => void;
  moveSection: (pageId: string, sectionId: string, dir: -1 | 1) => void;
  addField: (pageId: string, sectionId: string, type: string) => void;
  updateField: (
    pageId: string,
    sectionId: string,
    fieldId: string,
    patch: Partial<SurveyField>,
  ) => void;
  deleteField: (pageId: string, sectionId: string, fieldId: string) => void;
  moveField: (pageId: string, sectionId: string, fieldId: string, dir: -1 | 1) => void;
  select: (selection: BuilderSelection) => void;
};
