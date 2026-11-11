---
name: document-generation
description: Generates professional technical documentation, API specifications, and architecture manuals.
required_tools: ["file_read", "file_write"]
safety_tier: SAFE
---

# Document Generation Skill

Produces high-standard technical documentation and architecture blueprints.

## Procedure
1. Read existing source code or schemas via `file_read`.
2. Extract classes, functions, and API routes.
3. Generate structured markdown document with Mermaid diagrams and tables.
4. Write output document to target markdown artifact.
