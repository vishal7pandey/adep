---
id: BLK-058
type: feature
title: "Error boundaries, crash reporting, and user-facing error states"
priority: medium
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T23:59:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-026]
tags: [frontend, error-handling, reliability, boundary, crash-reporting]
---

## Description

Add error boundaries and user-facing error states so the frontend
doesn't crash silently or show a blank screen when something fails.

## Motivation

Agentic apps have many failure modes: SSE disconnects, API errors,
LLM hallucinations, malformed tool responses. The UI must degrade
gracefully and tell the user what happened.

## Components to Add

### 1. Global Error Boundary
- Wrap the entire app in `components/ErrorBoundary.tsx`
- Catches React render errors
- Shows a fallback screen:
  - Error icon (lucide `AlertTriangle`)
  - "Something went wrong" message
  - Error ID (timestamp + short hash)
  - "Reload page" button
  - "Copy error" button for support

### 2. Pane-Level Error Boundaries
- Each pane has its own boundary so one broken pane doesn't take down
  the whole workbench
- Pane 1 error: "Could not load trace stream"
- Pane 2 error: "Could not load extracted data"
- Pane 3 error: "Could not load document viewer"
- Each has a "Retry" button

### 3. API Error States
- `lib/api.ts` wraps fetch errors and returns structured errors:
  ```typescript
  export interface APIError {
    status: number;
    code: string;
    message: string;
    details?: any;
  }
  ```
- Components show user-friendly messages based on `code`
  - `RUN_NOT_FOUND`: "Run not found. It may have been deleted."
  - `BUDGET_EXCEEDED`: "Budget limit reached. Contact admin."
  - `RATE_LIMITED`: "Too many requests. Please wait."
  - `PROVIDER_ERROR`: "Document provider error. Try a different file."

### 4. SSE Reconnection and Error State
- If SSE disconnects:
  1. Show warning banner: "Connection lost. Reconnecting..."
  2. Auto-retry with exponential backoff (2s, 4s, 8s, 16s)
  3. After 4 failures, show error: "Connection lost. [Reconnect]"
- If backend sends `error` SSE event, display it in Pane 1 with red
  border and details

### 5. Form Validation Errors
- Skill Editor, Template Editor, Definition Builder show inline
  validation errors
- Required fields in red with message
- JSON view in Pane 2 shows parse errors with line number

### 6. 404 and Error Pages
- `/404` route for unknown URLs
- Generic error page for 500s
- Both use LTTS brand colors

## Acceptance Criteria

- [ ] Global error boundary wraps app
- [ ] Pane-level boundaries for each workbench pane
- [ ] API errors return structured `APIError` objects
- [ ] User-friendly error messages for common error codes
- [ ] SSE auto-retry with exponential backoff
- [ ] SSE disconnect UI state (reconnecting / failed)
- [ ] Form validation errors inline in editors
- [ ] 404 and generic error pages
- [ ] Error logs sent to console with context (no PII leak)
- [ ] Test: throw in component → boundary catches and shows fallback
- [ ] Test: disconnect network → SSE retries then shows error

## Constraints

- No external crash reporting service in v1 (Sentry is v2)
- Error messages must not leak secrets or full stack traces to user [CM]
- Error IDs help support correlate logs

## Dependencies

- BLK-026 (frontend scaffold)
- BLK-029, BLK-030, BLK-031 (editors — need validation errors)
