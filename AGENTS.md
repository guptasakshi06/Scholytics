# ScholarReady workspace instructions

## Start here

Read `HANDOFF.md` in this directory before planning or changing this project. It is the persistent project brief, sprint backlog, current status, and continuation protocol. Follow more recent explicit user instructions if they change that brief.

When the user asks to continue, gives the handoff path, or requests the next sprint:

1. Read the complete handoff, its current-state section, and the relevant prior sprint history. Inspect the actual workspace and changes; do not assume a prior chat's claims are correct.
2. Resume an unfinished sprint first; otherwise execute the first eligible `NOT_STARTED` sprint. By default complete **one sprint per chat**. Do not stop after offering a plan or require the user to repeat the brief. Do not start another sprint unless the user asks.
3. Mark the selected sprint `IN_PROGRESS` in the handoff before implementation. Work through its tasks and acceptance criteria, running the appropriate checks.
4. Before every final response, including partial or blocked work, update `HANDOFF.md` and append a factual entry to `docs/SPRINT_HISTORY.md`. Record files, exact runnable commands, checks and outcomes, limitations, blockers, and the next action. Never mark unrun checks as passed or implementation as done merely because files exist.
5. Mark a sprint `DONE` only when all its acceptance criteria have evidence. Keep unfinished work `IN_PROGRESS`, or `BLOCKED` when a concrete external prerequisite prevents further useful work. Keep its pointer selected until it is complete. These are document statuses, not instructions to create or update a tool-managed goal.
6. Give the user a short outcome, verification summary, and the same handoff path for their next chat. Do not copy the whole handoff into the final response.

## Project boundaries

- This is a local academic Python project for Sakshi Gupta and Jigisha Baiswar, Project 042. Scope is document readiness, not certificate authentication or scholarship approval.
- Make DIP contributions, baseline comparisons, uncertainty, dataset provenance, and reproducible evaluation visible.
- Use the same analysis pipeline from CLI, evaluation, and Streamlit. No UI-only business rules.
- Do not fabricate data, results, citations, course requirements, work by students, or dependency compatibility.
- Preserve applicant/source grouping and untouched final test data. Do not use reference annotations as inference input.
- Do not upload applicant documents to external services or add paid APIs to the core workflow. Use clearly labelled fictional data by default.
- Plan step by step. Do not implement all sprints at once, deploy, publish, push, or contact anyone as part of an ordinary sprint.
- No sub-agents are required by these instructions. Execute normally unless the user explicitly requests delegation.
- Code changes need checks proportionate to the changed behavior. Documentation-only changes need link/status consistency checks, not invented application tests.

The initial handoff-creation chat authored planning files only. No application code, environment installation, model training, or measured results exist at that starting point.
