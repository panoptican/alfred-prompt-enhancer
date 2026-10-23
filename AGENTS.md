# Prompt Enhancer for Alfred

Shareable Alfred workflow that rewrites selected text into a prompt for a specific Claude or GPT model.

## Layout

- `workflow/` is exactly what ships in the `.alfredworkflow` file.
  - `info.plist`: Alfred objects, Universal Actions, install settings, About text and version.
  - `enhance.zsh`: all the logic. The model list is at the top.
  - `templates/<mode>.md`: one template per mode.
- `build.sh` checks the workflow and zips it into `dist/` (not committed).

## Rules

- Templates stay neutral: no names, clients or personal details. Personal context comes only from the `{{ABOUT_USER}}` and `{{MISHEARD_NAMES}}` placeholders.
- The bracketed-gap rule (at most three `[question?]` gaps, "Assume …" lines for smaller ones) uses the same wording in every template.
- Adding a mode takes three things that must match: a line in `enhance.zsh`, `templates/<mode>.md`, and a Universal Action that sets `ENHANCER_MODE`. `build.sh` checks that they agree.

## Checks

- `./build.sh` validates the plist, the script syntax and the mode/template/action match.
- To check a mode end to end, run the script the way Alfred does, from `workflow/`:
  `ENHANCER_MODE=sonnet-5-5 alfred_workflow_bundleid=net.spidleweb.prompt-enhancer zsh enhance.zsh "some test text"`
  The result goes to the clipboard and the job folder under the cache directory.
