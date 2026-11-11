---
name: deployment
description: Containerization, Dockerfile generation, render.yaml / docker-compose specs, and deploy validation.
required_tools: ["file_read", "file_write", "terminal_exec"]
safety_tier: PRIVILEGED
---

# Deployment & Containerization Skill

Automates build pipelines, Docker containerization, and cloud deployment manifests.

## Procedure
1. Inspect project runtime and entrypoints.
2. Generate multi-stage Dockerfile with non-root user and minimal footprint.
3. Generate orchestration configs (`docker-compose.yml`, `render.yaml`).
4. Validate container build inside sandbox using `terminal_exec`.
