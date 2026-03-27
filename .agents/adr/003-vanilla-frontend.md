# ADR-003: Vanilla HTML/CSS/JS frontend (no build step)

**decision**: Build the frontend as a single-page application using vanilla
HTML, CSS, and JavaScript — no framework, no build step.

**rationale**: The UI has a single view (table + filter editor). This does not
warrant React/Vue/Svelte complexity. A build step would require Node.js in the
Docker image (bloating it on Raspberry Pi) or a separate CI build pipeline.
Vanilla JS served as static files keeps the Dockerfile simple (`COPY rootfs /`)
and the add-on image small. The ingress base path (`X-Ingress-Path`) is easily
handled by injecting a `<base>` tag or a JS global.

**rejected alternatives**:
- React/Vue/Svelte SPA: requires Node.js build toolchain; adds 50-100MB to
  the image; unnecessary for a single-view data table + form UI.
- Server-side rendered templates (Jinja2): viable but loses client-side
  interactivity for live filter preview without full page reloads.
- HTMX: interesting but introduces a dependency; the team is more familiar
  with vanilla JS for this scope.

**revisit if**: the UI grows beyond 2-3 views or requires complex state
management (e.g., multi-step wizards, drag-and-drop filter builder).
