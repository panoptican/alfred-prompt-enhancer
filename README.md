# Prompt Enhancer for Alfred

Prompt Enhancer turns rough text into a clear prompt for the model you're about to paste it into. Select the text anywhere on your Mac, pick the model from Alfred's Universal Actions, and the rewritten prompt is copied to your clipboard shortly after.

I built it because I dictate most of my prompts, and dictation comes out as a ramble full of false starts and self-corrections. The workflow keeps what I meant and drops the rest. It holds on to the request itself, so a question stays a question and a review doesn't turn into a fix. When a fact that would change the result is missing, such as which project or where the output should go, it leaves a short bracketed question in the prompt, like `[which prototype?]`, so I can fill it in before I paste.

Each action uses a template written for that model. The workflow includes Claude Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.2, and GPT 6.1 Sol, GPT 6 Luna and GPT 6 Astra.

## Requirements

You need macOS with [Alfred 5](https://www.alfredapp.com) and the Powerpack, which Universal Actions require.

The Claude actions run through [Claude Code](https://claude.com/claude-code) and the GPT actions run through the [Codex CLI](https://github.com/openai/codex). Install the one you plan to use, sign in with `claude auth login` or `codex login`, and make sure your account has access to those models.

The workflow doesn't call any model API itself. Each rewrite runs through that CLI on your Mac, using whatever account the CLI is signed in to. If you signed in with a Claude or ChatGPT subscription, rewrites count toward that plan's usage limits like any other session. If the CLI uses an API key instead, each rewrite is billed to that key.

## Install

1. Download `Prompt-Enhancer-<version>.alfredworkflow` from the latest release.
2. Double-click the file and choose Import in Alfred.
3. Fill in any of the optional settings described below, then choose Import again.

## Use

1. Select text in any app.
2. Press your Universal Actions hotkey, which you can set in Alfred Preferences under Features → Universal Actions.
3. Choose the action for the model you'll paste into, such as "PE: Claude Sonnet 5.5".
4. Paste when the "Prompt enhanced" notification appears.

The rewrite runs in the background, so you can keep working while it finishes. Most take somewhere between a few seconds and half a minute. If you start another request, only the latest accepted request can update your clipboard, even if it fails. Older results are saved in the cache and reported as superseded.

## Settings

All settings are optional. To change them later, open Alfred Preferences, select Prompt Enhancer under Workflows, and choose Configure Workflow.

- Effort sets how much the model thinks before rewriting. Choose Low, Medium or High. Medium is the default.
- About you is a short description of yourself, such as "a backend developer who works mostly in Python", so prompts fit your role and voice.
- Misheard names is a comma-separated list of names your dictation tends to get wrong, such as "Figma, Raycast, Supabase". The rewrite uses it to correct them.
- Templates folder points to a folder of your own templates, described in the next section.

## Templates

Each action has a bundled template in the workflow's `templates` folder: `opus-5-5.md`, `sonnet-5-5.md`, `haiku-5-5.md`, `fable-5-2.md`, `gpt-6.1-sol.md`, `gpt-6-luna.md` and `gpt-6-astra.md`.

To change a template, copy it into your templates folder and edit the copy without renaming it. The workflow uses your copy instead of the bundled one, and updating the workflow leaves your copy alone.

Your folder only needs the templates you've changed, because any action without a matching file keeps using its bundled template. Files are matched by exact name, so the workflow ignores a renamed copy without warning. It also ignores files that don't match one of the seven actions, so adding a template can't add a new model.

Two lines in each template come from your settings. `{{ABOUT_USER}}` becomes "About the user" followed by your description, and `{{MISHEARD_NAMES}}` becomes a sentence listing your names. When a setting is blank, its line is removed.

## Updating a model

The model IDs are listed at the top of `enhance.zsh` in the workflow folder. To move an action to a newer model, change its ID there.

Adding a model takes three matching pieces: a line in that list, a template named after the new mode, and a Universal Action that sets `ENHANCER_MODE` to the mode.

The workflow keeps one action per model family. When a new version replaces an older one, such as Fable 5.2 replacing Fable 5.1, the old action becomes the new one. It keeps its place in Alfred and gets the new name and a template written for the new version. The old template moves to `archive/templates/` in this repository and no longer ships with the workflow.

If you had your own copy of the old template in your templates folder, the workflow stops using it after the update, because its name no longer matches an action. Copy the new bundled template into your folder and make your changes again.

## Troubleshooting

If a notification says Claude Code or Codex isn't installed or isn't signed in, run the command it gives in Terminal and try again.

If the CLI is installed but the workflow can't find it, the cause is usually Alfred's limited PATH. The workflow already checks the same locations your login shell uses. If it still fails, open the workflow in Alfred Preferences, choose the `[x]` button to add an environment variable, and set `CLAUDE_BIN` or `CODEX_BIN` to the CLI's full path.

Each run saves its request, output and any errors in Alfred's workflow cache, at `~/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/net.spidleweb.prompt-enhancer/`. The workflow keeps the 20 most recently completed runs, plus unfinished runs, because each one includes the text you selected. Unfinished runs are preserved so cleanup cannot delete a job while it is working.

## Build a release

```bash
./build.sh
```

The script checks the workflow and writes `dist/Prompt-Enhancer-<version>.alfredworkflow`, taking the version from `workflow/info.plist`.

## License

MIT. See [LICENSE](LICENSE).
