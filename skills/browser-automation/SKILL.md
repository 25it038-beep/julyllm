---
name: browser-automation
description: Autonomous web browsing, form-filling, extraction, and screenshot validation.
required_tools: ["browser_navigate", "file_write"]
safety_tier: SAFE
---

# Browser Automation Skill

Automates web interactions, data extraction, and visual verification.

## Procedure
1. Navigate to target URL using `browser_navigate` with action `navigate`.
2. Extract text and DOM headings to verify page loaded properly.
3. Extract forms or links if interactive navigation is required.
4. Save extracted content or structured datasets to workspace files using `file_write`.
