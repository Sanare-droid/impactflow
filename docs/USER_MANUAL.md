# ImpactFlow — User Manual

**Audience:** organization admins, program managers, MEAL officers, field staff, and executives  
**Product:** ImpactFlow — MEAL operating system for development organizations  
**Related:** [DEPLOYMENT_PLAN.md](./DEPLOYMENT_PLAN.md) · [WHITE_LABEL.md](./WHITE_LABEL.md) · Epic guides in `/docs`

---

## 1. What ImpactFlow is

ImpactFlow helps organizations plan, deliver, monitor, and report development programs in one multi-tenant workspace. Each **organization** is a private tenant: your programs, beneficiaries, surveys, AI, and integrations never mix with another organization’s data.

You can:

- Manage programs, projects, finance, and MEAL results  
- Collect field data (surveys, offline-ready field ops)  
- Automate approvals with workflows  
- Ask grounded questions with AI Copilot  
- Produce executive and donor reports  
- Connect external tools (Kobo, Slack, Sheets, and more)  
- White-label the workspace under your brand  

---

## 2. Getting started

### 2.1 Sign in

1. Open your ImpactFlow URL (or your organization’s custom domain).  
2. Sign in with email and password.  
3. If MFA is enabled, enter the authenticator code.  
4. You land on the **Dashboard** (`/app`).

If you were invited, open the invite link first, set a new password, then sign in.

### 2.2 Onboarding wizard (recommended for new orgs)

Go to **Onboarding** (`/app/onboarding`).

| Step | What you do |
|------|-------------|
| Sector & country | Choose your sector (health, education, WASH, …) and ISO country |
| Theme | Apply a white-label color preset |
| Checklist | Mark project, invites, AI, integrations, notifications as done |
| Finish | Celebrate completion and open the dashboard |

You can return anytime; progress is saved per organization.

### 2.3 Choose your theme (light / dark)

Use the sun/moon control in the sidebar (or mobile header) to switch themes. Prefer **reduced motion** in your OS settings if animations bother you — ImpactFlow respects `prefers-reduced-motion`.

---

## 3. Navigation map

The left sidebar groups modules. Keyboard users can press **Skip to main content** (visible on Tab) to jump past the nav.

| Group | Modules | Typical users |
|-------|---------|----------------|
| **Workspace** | Dashboard, Notifications | Everyone |
| **Delivery** | Programs, Projects, Tasks | Managers, officers |
| **Finance** | Donors, Grants, Budgets, Finance | Finance, managers |
| **MEAL** | Theory of Change, Logframes, Indicators, Monitoring, Evaluations, Surveys | MEAL officers |
| **Field** | Field Operations, Communities, Households, Beneficiaries | Field / MEAL |
| **Insights** | Executive, Reports, Analytics, Dashboards, Maps, Evidence | Leadership, MEAL |
| **AI** | Copilot, Predictions, Narratives, Knowledge | Power users |
| **Platform** | Workflows, Marketplace, Integrations, Developer, White label, Onboarding | Admins |
| **Admin** | Users, Roles, Organization, Billing, Success, Operations, Audit, Settings | Org admins |

What you see depends on your **role permissions**. If a page is missing, ask an org admin.

---

## 4. Core delivery & MEAL

### 4.1 Programs → Projects → Tasks

1. **Programs** — create the portfolio container (e.g. “Country Health Portfolio”).  
2. **Projects** — add funded or operational projects under a program.  
3. **Tasks** — assign delivery work; track status from the Tasks list.

Always pick the correct program/project so finance and MEAL stay linked.

### 4.2 Theory of Change & logframes

- **Theory of Change** — document pathways from activities to impact.  
- **Logframes** — structure results, indicators, and assumptions for donors.  
- **Indicators** — define metrics and targets.  
- **Monitoring** — enter results against indicators.  
- **Evaluations** — capture evaluation studies and findings.

### 4.3 Surveys

Use **Surveys** to design forms, publish versions, assign collectors, and review responses. Attachments and assignments stay inside your organization.

### 4.4 Field operations

**Field Operations** supports device registration, sync sessions, and conflict review for offline-capable field work. Register devices before large field deployments; resolve sync conflicts promptly so monitoring stays accurate.

### 4.5 Communities, households, beneficiaries

Register **communities**, then **households** and **beneficiaries**. Link people to projects where your methodology requires it. Treat personal data carefully — only staff with beneficiary permissions should access these screens.

---

## 5. Finance

| Module | Use it to |
|--------|-----------|
| **Donors** | Maintain donor profiles |
| **Grants** | Track grant awards, periods, and status |
| **Budgets** | Plan budget lines against grants/projects |
| **Finance** | Record transactions and burn |

Keep grant periods aligned with project dates so executive burn charts stay meaningful.

---

## 6. Insights & reporting

### 6.1 Executive

**Executive** (`/app/executive`) summarizes portfolio health for board, donor, or management audiences. Use filters (program / project) before exporting or generating briefs.

### 6.2 Reports & analytics

- **Reports** — build, version, and export donor/MEAL narratives.  
- **Analytics** — explore performance charts.  
- **Dashboards** — save reusable board layouts.  
- **Maps** — visualize geographic layers.  
- **Evidence** — store supporting files tied to results.

When exporting, confirm you are in the correct organization if you belong to more than one.

---

## 7. AI features

| Module | Purpose |
|--------|---------|
| **AI Copilot** | Ask questions grounded in your org’s data and tools |
| **Predictions** | Review risk / delivery predictions |
| **Narratives** | Generate structured narrative drafts for reports |
| **Knowledge** | Upload documents the Copilot can retrieve |

**Good practice**

- Prefer specific questions (“burn rate for Grant X this quarter”) over vague prompts.  
- Always review AI text before sending to donors.  
- Do not paste secrets or personal identifiers into prompts unnecessarily.

AI availability may depend on your **subscription plan** and feature flags.

---

## 8. Workflows & automation

**Workflows** let you define multi-step processes (approvals, notifications, actions).

Typical uses:

- Report approval chains  
- Alert when indicators miss targets  
- Trigger follow-ups after survey submission  

Publish a workflow version before relying on it in production. Approvers need the `workflows:approve` permission.

---

## 9. Marketplace & integrations

### 9.1 Marketplace

**Marketplace** (`/app/marketplace`) lists templates and connectors (Kobo, Slack, ODK, donor packs, and more).

- **Install** — enables the app for your org; matching connectors may auto-enable in Integrations.  
- **Uninstall / disable** — change installation status when you no longer need it.

### 9.2 Integrations Hub

**Integrations** (`/app/integrations`):

1. Browse the connector gallery.  
2. Enable a connector and enter credentials (stored encrypted).  
3. Run **health** checks and **sync** (including dry-run).  
4. Configure **field mappings** if transforming data.  
5. Monitor jobs and webhook delivery.

Never share API secrets in chat; rotate keys from the Integrations / API Keys UI if compromised.

### 9.3 Developer portal

**Developer** (`/app/developer`) documents events, OpenAPI access patterns, and plugin registration points for technical staff. See also [PLUGIN_SDK.md](./PLUGIN_SDK.md).

---

## 10. White label & branding

**White label** (`/app/branding`) controls how partners see your workspace:

- Product name, tagline, logo  
- Primary / secondary / accent colors  
- Custom domain  
- Support email  
- Terms & privacy URLs, footer text  
- Hide “Powered by ImpactFlow” (plan permitting)

Use **live preview** on the right before saving. For DNS steps, see [CUSTOM_DOMAIN.md](./CUSTOM_DOMAIN.md) and the **Organization** admin domains section.

---

## 11. Administration

### 11.1 Users & roles

| Role (typical) | Intended for |
|----------------|--------------|
| Organization Admin | Full tenant control |
| Program Manager | Delivery + reporting |
| MEAL Officer | Indicators, surveys, evidence |
| Field Officer | Field sync & beneficiaries (scoped) |
| Viewer | Read-only insights |

**Users** — invite teammates, deactivate leavers.  
**Roles** — review permission codes; prefer least privilege.

### 11.2 Organization admin console

**Organization** (`/app/organization`) is the tenant control center:

- Profile (name, country, timezone, locale)  
- Regional settings (currency, financial year, retention)  
- Custom domains (add → DNS TXT/CNAME → Verify)  
- SSO draft (OIDC issuer / client ID; secrets encrypted)  
- Language packs available to the platform  
- Feature access chips (resolved flags)  
- Backups & **Export all data**

### 11.3 Billing & feature flags

**Billing** (`/app/billing`):

- View current plan and seats  
- Switch Free / Starter / Professional / Enterprise / Government (as offered)  
- Toggle monthly vs annual  
- See which features are enabled for your org  

Feature access is driven by plan + org overrides. Contact your platform operator for custom contracts.

### 11.4 Security settings

**Settings** (`/app/settings`) — password change, MFA enrollment.  
**Audit** (`/app/audit`) — who changed what (invites, branding, billing, integrations).

### 11.5 Customer success & operations

- **Success** — health score, adoption, recommended next actions.  
- **Operations** — platform component health (for admins).  

Use Success recommendations to finish onboarding and connect integrations.

---

## 12. Notifications

**Notifications** (`/app/notifications`) lists in-app alerts (workflow decisions, publishes, predictions, and more). Unread counts appear on the nav badge. Mark items read individually or all at once.

---

## 13. Accessibility tips

- Navigate with keyboard: Tab / Shift+Tab; Enter to activate.  
- Use **Skip to main content** at the top of the app shell.  
- Enable OS **high contrast** or **larger text** as needed; ImpactFlow uses scalable typography.  
- Prefer **reduced motion** if animations are distracting.  
- Charts and tables should be paired with textual summaries in reports when presenting to screen-reader users.

---

## 14. Common tasks (quick recipes)

### Invite a colleague

1. Admin → **Users** → invite by email.  
2. Assign a role (manager / meal_officer / viewer…).  
3. They set a password from the invite link.

### Publish a donor report

1. Enter monitoring results for the period.  
2. Open **Reports** or **Executive** → build / generate narrative.  
3. Review AI text → save version → export.

### Connect Kobo (or similar)

1. **Marketplace** → install Kobo connector (or enable in Integrations).  
2. Enter server URL and token.  
3. Run health → configure mapping → sync.

### Brand a partner portal

1. **Onboarding** or **White label** → apply theme.  
2. Upload logo URLs and support contacts.  
3. **Organization** → add custom domain → verify DNS.  
4. Test public branding URL / host resolve.

### Leave the organization safely

1. Export data if you are offboarding (**Organization** → Export).  
2. Deactivate users you no longer need.  
3. Rotate API keys and integration secrets.

---

## 15. Troubleshooting

| Problem | What to try |
|---------|-------------|
| Cannot see a module | Ask admin to check your role permissions |
| Login works but data empty | Confirm you are in the correct organization |
| Invite email missing | Check spam; ask ops if SMTP is configured (staging may stub) |
| Integration unhealthy | Re-check credentials; run health; view monitoring errors |
| AI errors | Confirm plan includes AI and that ops set `OPENAI_API_KEY` |
| Domain not branding | Domain must be **verified** and branding **enabled** |
| Sync conflicts | Open Field Operations conflict log and resolve before re-sync |

Still stuck? Contact your organization’s support email (set under White label) or your ImpactFlow operator.

---

## 16. Privacy & responsible use

- Access only data you need for your role.  
- Do not export beneficiary PII to unsecured channels.  
- Product analytics (where enabled) are for platform improvement — treat field data as confidential.  
- Review audit logs after sensitive changes (SSO, billing, API keys).

---

## 17. Where to learn more

| Topic | Document |
|-------|----------|
| Deploy / go-live | [DEPLOYMENT_PLAN.md](./DEPLOYMENT_PLAN.md), [DEPLOY.md](./DEPLOY.md) |
| Architecture | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| Surveys | [EPIC1_FORMS_ENGINE.md](./EPIC1_FORMS_ENGINE.md) |
| AI Copilot | [EPIC2_AI_COPILOT.md](./EPIC2_AI_COPILOT.md) |
| Workflows | [EPIC3_WORKFLOWS.md](./EPIC3_WORKFLOWS.md) |
| Field ops | [EPIC4_FIELD_OPS.md](./EPIC4_FIELD_OPS.md) |
| Executive reporting | [EPIC5_EXECUTIVE.md](./EPIC5_EXECUTIVE.md) |
| Integrations | [EPIC6_INTEGRATIONS_HUB.md](./EPIC6_INTEGRATIONS_HUB.md) |
| Enterprise SaaS | [EPIC7_ENTERPRISE.md](./EPIC7_ENTERPRISE.md) |
| Plugins | [PLUGIN_SDK.md](./PLUGIN_SDK.md) |
| Security sign-off | [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md) |
