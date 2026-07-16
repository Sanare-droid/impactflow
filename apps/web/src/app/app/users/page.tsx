"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

export default function UsersPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/users`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("if_access_token")}`,
            "X-Organization-Id": localStorage.getItem("if_organization_id") ?? "",
          },
        },
      );
      if (!res.ok) throw new Error("Unable to load users");
      return res.json() as Promise<{
        items: Array<{
          id: string;
          status: string;
          user?: {
            email: string;
            first_name: string;
            last_name: string;
          };
          role?: { name: string; slug: string };
        }>;
      }>;
    },
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Users</h1>
        <p className="mt-2 text-stone-500">
          Organization members and their assigned roles.
        </p>
      </div>

      <Card>
        <CardTitle>Members</CardTitle>
        <CardDescription>
          All memberships are tenant-scoped and audited.
        </CardDescription>
        {error && (
          <p className="mt-4 text-sm text-rose-600">{(error as Error).message}</p>
        )}
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Email</th>
                <th className="pb-3 font-medium">Role</th>
                <th className="pb-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={4}>
                    Loading…
                  </td>
                </tr>
              )}
              {data?.items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-medium">
                    {item.user
                      ? `${item.user.first_name} ${item.user.last_name}`
                      : "—"}
                  </td>
                  <td className="py-3 text-stone-600 dark:text-stone-300">
                    {item.user?.email ?? "—"}
                  </td>
                  <td className="py-3">{item.role?.name ?? "—"}</td>
                  <td className="py-3">
                    <span className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-800 dark:bg-teal-950 dark:text-teal-200">
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
