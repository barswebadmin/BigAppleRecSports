# Slack Deno SDK — Official Doc Links

Index of the Slack platform docs relevant to the Deno Slack apps in this repo. (Replaces the vendored copies previously in `slack-apps/deno-instructions/`.)

## Core concepts

- [Developing with Deno](https://docs.slack.dev/tools/deno-slack-sdk/guides/developing-with-deno)
- [Developing with TypeScript](https://docs.slack.dev/tools/deno-slack-sdk/guides/developing-with-typescript)
- [Creating workflows](https://docs.slack.dev/tools/deno-slack-sdk/guides/creating-workflows)
- [Creating custom functions](https://docs.slack.dev/tools/deno-slack-sdk/guides/creating-custom-functions)
- [Slack functions catalog](https://docs.slack.dev/reference/functions)

## Triggers

- [Using triggers](https://docs.slack.dev/tools/deno-slack-sdk/guides/using-triggers)
- [Creating link triggers](https://docs.slack.dev/tools/deno-slack-sdk/guides/creating-link-triggers)

## Interactivity & UI

- [Adding interactivity](https://docs.slack.dev/tools/deno-slack-sdk/guides/adding-interactivity)
- [Creating a form](https://docs.slack.dev/tools/deno-slack-sdk/guides/creating-a-form)
- [Creating an interactive message](https://docs.slack.dev/tools/deno-slack-sdk/guides/creating-an-interactive-message)
- [Creating an interactive modal](https://docs.slack.dev/tools/deno-slack-sdk/guides/creating-an-interactive-modal)

## Running & deploying

- [Developing locally](https://docs.slack.dev/tools/deno-slack-sdk/guides/developing-locally)
- [Deploying to Slack](https://docs.slack.dev/tools/deno-slack-sdk/guides/deploying-to-slack)

## Tutorials

- [Open authorization](https://docs.slack.dev/tools/deno-slack-sdk/tutorials/open-authorization) — OAuth2 walkthrough built on the [deno-simple-survey](https://github.com/slack-samples/deno-simple-survey) sample (a reaction-triggered, multi-workflow app worth reading even ignoring the OAuth parts)

## Patterns worth knowing (extracted from the tutorials)

- **Project structure gotchas:** `.slack/` must be checked into version control, but `.slack/apps.dev.json` is gitignored and must not be. `import_map.json` controls Deno module resolution; `assets/` holds the app icon.
- **`outgoingDomains` is mandatory for external HTTP.** Any `fetch()` to a non-Slack API fails unless the domain is listed in the manifest (e.g. `outgoingDomains: ["sheets.googleapis.com"]`).
- **Workflows can be triggered by reactions (reacji).** The survey sample starts a workflow when 📋 is added to any message — no slash command or shortcut needed. Reaction-triggered apps work immediately after deploy, unlike link-trigger apps.
- **Functions can mint triggers at runtime.** A custom function can call `client.workflows.triggers.create<typeof SomeWorkflow.definition>({type: "shortcut", ...})` to generate a per-entity shortcut URL on the fly (the sample creates one trigger per survey). Triggers are not static config. Runtime values use `{{data.interactivity}}`-style template placeholders.
- **Workflows are typed pipelines.** Step outputs feed later steps' inputs (`workflow.addStep(Fn, { x: prevStep.outputs.y })`); anything a later step needs must be threaded through as explicit input/output parameters — there is no shared state between steps.
- **Production hygiene: a scheduled "maintenance job" workflow.** The sample runs a daily workflow that re-ensures the bot is a member of every channel its reaction-event triggers watch — recommended pattern, since event triggers silently stop firing if the bot gets removed.
