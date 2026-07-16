# Kubernetes readiness (Epic 7)

Minimal manifests for horizontal API scaling. Adapt images, secrets, and ingress to your cluster.

## Layout

- `api-deployment.yaml` — API Deployment + Service + probes
- `api-hpa.yaml` — HorizontalPodAutoscaler stub
- `configmap-env.example.yaml` — non-secret config example

## Notes

- Run migrations as a Job or init container (`alembic upgrade head`) before rolling new pods.
- Use managed Postgres + Redis; object storage for backups/media.
- Terminate TLS at ingress; map custom domains to the ingress controller.
- Prefer rolling updates with `maxUnavailable: 0` for zero-downtime deploys.
- See `docs/DEPLOY.md` for compose-based production and `docs/EPIC7_ENTERPRISE.md` for SaaS features.
