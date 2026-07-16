"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tabs } from "@/components/ui/tabs";
import { SurveyBuilder } from "@/components/surveys/SurveyBuilder";
import { SurveyCapture } from "@/components/surveys/SurveyCapture";
import { SurveyResponses } from "@/components/surveys/SurveyResponses";
import { SurveyAnalytics } from "@/components/surveys/SurveyAnalytics";
import { SurveyVersions } from "@/components/surveys/SurveyVersions";
import { SurveyAssignments } from "@/components/surveys/SurveyAssignments";

const TABS = [
  { id: "builder", label: "Builder" },
  { id: "capture", label: "Capture" },
  { id: "responses", label: "Responses" },
  { id: "analytics", label: "Analytics" },
  { id: "assignments", label: "Assignments" },
  { id: "versions", label: "Versions" },
];

export default function SurveyDetailPage() {
  const params = useParams<{ id: string }>();
  const surveyId = params.id;
  const [tab, setTab] = useState("builder");

  const { data, isLoading } = useQuery({
    queryKey: ["survey", surveyId],
    queryFn: () => api.getSurvey(surveyId),
  });

  if (isLoading || !data) {
    return <p className="text-sm text-stone-400">Loading survey…</p>;
  }

  const { survey, version } = data;

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <Link href="/app/surveys" className="text-sm text-teal-700 dark:text-teal-300">
          ← Surveys
        </Link>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-semibold tracking-tight">{survey.name}</h1>
          <StatusBadge status={survey.status} />
        </div>
        <p className="mt-2 flex flex-wrap items-center gap-2 text-stone-500">
          <span>{survey.code}</span>
          <span>· v{survey.current_version}</span>
          {survey.category && <span>· {survey.category}</span>}
          {survey.is_anonymous && <span>· Anonymous</span>}
        </p>
        {survey.description && <p className="mt-1 max-w-2xl text-sm text-stone-500">{survey.description}</p>}
      </div>

      <Tabs items={TABS} active={tab} onChange={setTab} />

      {tab === "builder" && <SurveyBuilder survey={survey} version={version} />}
      {tab === "capture" && <SurveyCapture survey={survey} version={version} />}
      {tab === "responses" && <SurveyResponses survey={survey} />}
      {tab === "analytics" && <SurveyAnalytics survey={survey} />}
      {tab === "assignments" && <SurveyAssignments survey={survey} />}
      {tab === "versions" && <SurveyVersions survey={survey} />}
    </div>
  );
}
