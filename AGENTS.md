# Prompt Enhancer for Alfred

Shareable Alfred workflow that rewrites selected text into a prompt for a specific Claude or GPT model.

## Layout

- `workflow/` is exactly what ships in the `.alfredworkflow` file.
  - `info.plist`: Alfred objects, Universal Actions, install settings, About text and version.
  - `enhance.zsh`: all the logic. The model list is at the top.
  - `templates/<mode>.md`: one template per mode.
  - `icon.png`: rendered from `assets/icon.svg`. Alfred has no light or dark icon variants, so the icon has to show up on both light and dark notification banners.
- `assets/icon.svg` is the icon's source. It doesn't ship. Render it with `resvg -w 256 -h 256 assets/icon.svg workflow/icon.png`.
- `build.sh` checks the workflow and zips it into `dist/` (not committed).
- `archive/templates/` holds templates for replaced models. They don't ship.

## Rules

- Templates stay neutral: no names, clients or personal details. Personal context comes only from the `{{ABOUT_USER}}` and `{{MISHEARD_NAMES}}` placeholders.
- The bracketed-gap rule (at most three `[question?]` gaps, "Assume …" lines for smaller ones) uses the same wording in every template.
- Adding a mode takes three things that must match: a line in `enhance.zsh`, `templates/<mode>.md`, and a Universal Action that sets `ENHANCER_MODE`. `build.sh` checks that they agree. The line's name is the action's name without "PE: ", and the tests check that.

## Replacing a model with a newer version

The workflow keeps one action per model family. To replace an older version, such as Fable 5.1 with Fable 5.2:

1. Write `templates/<new-mode>.md`, starting from the old template and changing it to follow the vendor's prompting guide for the new version. Keep the shared wording, such as the bracketed-gap rule, unless the guide gives a reason to change it in every template.
2. In `enhance.zsh`, replace the old mode's line with the new one.
3. In `info.plist`, edit the old Universal Action in place: change its name and its `ENHANCER_MODE`. Don't delete it and add a new one, because keeping its UID keeps its place in each user's Alfred.
4. Move the old template to `archive/templates/`. Archived templates don't ship, and no action can reach them. To roll back, move the file back and undo steps 2 and 3.
5. Update the model lists in `README.md`, raise the minor version in `info.plist`, and run the checks.

Keep the old action next to the new one only when some users can't reach the new model yet, for example during a staged rollout. Remove it in the next release.

## Checks

- `./build.sh` validates the plist, the script syntax, the mode/template/action match and the shared bracketed-gap wording.
- `python3 -m unittest discover -s tests` runs the offline process tests, about 40 seconds. They stub the CLIs, notifications, sound and clipboard, so they need no account.
- To check a mode end to end, run the script the way Alfred does, from `workflow/`:
  `ENHANCER_MODE=sonnet-5-5 alfred_workflow_bundleid=net.spidleweb.prompt-enhancer zsh enhance.zsh "some test text"`
  The result goes to the clipboard and the job folder under the cache directory.

## Releasing and the maintainer's own install

This repository is the only source. The maintainer's own Alfred install is the built workflow, not a separate copy, so one change updates both.

- To update the install, run `./build.sh` and open the new file in `dist/`. Alfred imports it over the installed version (same bundle ID) and keeps its settings.
- Personal details go only in the workflow's settings (About you, Misheard names), which Alfred stores in the installed workflow's `prefs.plist`, or in the templates folder. They never go in this repository.

To publish a release, after the version bump is committed on `main` and the checks pass:

1. Run `./build.sh`.
2. Tag the bump commit with an annotated tag named after the version, and push the tag: `git tag -a v1.2.0 -m "Prompt Enhancer 1.2.0"` then `git push origin main v1.2.0`.
3. Create the GitHub release from that tag, titled the same as the tag message, with the built file attached: `gh release create v1.2.0 dist/Prompt-Enhancer-1.2.0.alfredworkflow --title "Prompt Enhancer 1.2.0" --notes-file <notes>`. The notes say what changed for users and end with how to update.

Version 1.1.2 was bumped in `info.plist` but never tagged or released; its changes first shipped in 1.2.0. Releases go 1.1.1, then 1.2.0.

## Ship

- **Deploys by:** not deployed. Users install the `.alfredworkflow` attached to a GitHub release, which is built, tagged and published by hand (see above).
- **Merge:** commits go straight to `main`; there are no pull requests or merge commits so far.
- **Check live:** `gh release list` shows the new version as Latest, with its `.alfredworkflow` attached.
- **Checks:** `./build.sh` and `python3 -m unittest discover -s tests`, run by hand. No CI.
