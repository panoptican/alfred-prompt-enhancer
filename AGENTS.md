# Prompt Enhancer for Alfred

Shareable Alfred workflow that rewrites selected text into a prompt for a specific Claude or GPT model.

## Layout

- `workflow/` is exactly what ships in the `.alfredworkflow` file.
  - `info.plist`: Alfred objects, Universal Actions, install settings, About text and version.
  - `enhance.zsh`: all the logic. The model list is at the top.
  - `templates/<mode>.md`: one template per mode.
- `build.sh` checks the workflow and zips it into `dist/` (not committed).
- `archive/templates/` holds templates for replaced models. They don't ship.

## Rules

- Templates stay neutral: no names, clients or personal details. Personal context comes only from the `{{ABOUT_USER}}` and `{{MISHEARD_NAMES}}` placeholders.
- The bracketed-gap rule (at most three `[question?]` gaps, "Assume …" lines for smaller ones) uses the same wording in every template.
- Adding a mode takes three things that must match: a line in `enhance.zsh`, `templates/<mode>.md`, and a Universal Action that sets `ENHANCER_MODE`. `build.sh` checks that they agree.

## Replacing a model with a newer version

The workflow keeps one action per model family. To replace an older version, such as Fable 5.1 with Fable 5.2:

1. Write `templates/<new-mode>.md`, starting from the old template and changing it to follow the vendor's prompting guide for the new version. Keep the shared wording, such as the bracketed-gap rule, unless the guide gives a reason to change it in every template.
2. In `enhance.zsh`, replace the old mode's line with the new one.
3. In `info.plist`, edit the old Universal Action in place: change its name and its `ENHANCER_MODE`. Don't delete it and add a new one, because keeping its UID keeps its place in each user's Alfred.
4. Move the old template to `archive/templates/`. Archived templates don't ship, and no action can reach them. To roll back, move the file back and undo steps 2 and 3.
5. Update the model lists in `README.md`, raise the minor version in `info.plist`, and run the checks.

Keep the old action next to the new one only when some users can't reach the new model yet, for example during a staged rollout. Remove it in the next release.

## Checks

- `./build.sh` validates the plist, the script syntax and the mode/template/action match.
- To check a mode end to end, run the script the way Alfred does, from `workflow/`:
  `ENHANCER_MODE=sonnet-5-5 alfred_workflow_bundleid=net.spidleweb.prompt-enhancer zsh enhance.zsh "some test text"`
  The result goes to the clipboard and the job folder under the cache directory.
