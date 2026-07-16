/** Organization types offered at workspace registration. */
export const ORGANIZATION_TYPES = [
  { value: "ngo", label: "NGO / Civil society" },
  { value: "foundation", label: "Foundation / Philanthropy" },
  { value: "government", label: "Government / Ministry" },
  { value: "donor", label: "Donor / Bilateral agency" },
  { value: "un_agency", label: "UN / Multilateral" },
  { value: "private_sector", label: "Private sector / CSR" },
  { value: "research", label: "Research / University" },
  { value: "implementing_partner", label: "Implementing partner" },
  { value: "other", label: "Other" },
] as const;

export type OrganizationTypeValue = (typeof ORGANIZATION_TYPES)[number]["value"];
