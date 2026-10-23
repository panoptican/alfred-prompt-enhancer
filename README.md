# Prompt Enhancer for Alfred

Select some text, such as a rough speech-to-text dump, and turn it into a clear prompt written for the model you're about to paste it into. The rewritten prompt lands on your clipboard.

Each model gets its own template, tuned to that model's prompting guide:

- Claude Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1
- GPT 6.1 Sol, GPT 6 Luna and GPT 6 Astra

The rewrite keeps what you asked for. It cleans up filler and self-corrections, keeps your intent and constraints, and doesn't turn a question into a change. When a fact that would change the result is missing, such as which project or where output should go, it leaves a short bracketed question in the prompt, like `[which prototype?]`, so you can fill it in before you paste.

## Requirements

- macOS with [Alfred 5](https://www.alfredapp.com) and the Powerpack (Universal Actions need it).
- For the Claude actions: [Claude Code](https://claude.com/claude-code), signed in (`claude auth login`), with access to the models you use.
- For the GPT actions: the [Codex CLI](https://github.com/openai/codex), signed in (`codex login`), with access to the models you use.

You only need the CLI for the models you plan to use.

## Install

1. Download `Prompt-Enhancer-<version>.alfredworkflow` from the latest release.
2. Double-click it and choose **Import** in Alfred.
3. Fill in any settings you want (all optional, see below).

## Use

1. Select text in any app.
2. Open Universal Actions (by default, select the text and press the Universal Actions hotkey, or press → on a result in Alfred).
3. Pick the "PE:" action for the model you'll paste into, such as **PE: Claude Sonnet 5.5**.
4. Wait for the "Prompt enhanced" notification, then paste.

The rewrite runs in the background, so you can keep working. Most rewrites take a few seconds to half a minute.

## Settings

Open Alfred Preferences → Workflows → Prompt Enhancer → **Configure Workflow**.

- **Effort**: how much the model thinks before rewriting. Low, Medium (default) or High.
- **About you**: a short phrase such as "a backend developer who works mostly in Python". It helps prompts match your role and voice.
- **Misheard names**: comma-separated names your dictation often gets wrong, such as "Figma, Raycast, Supabase". The rewrite uses them to fix mis-transcriptions.
- **Templates folder**: a folder of your own templates (see below).

## Templates

The bundled templates are in the workflow's `templates/` folder, one per action: `opus-5-5.md`, `sonnet-5-5.md`, `haiku-5-5.md`, `fable-5-1.md`, `gpt-6.1-sol.md`, `gpt-6-luna.md` and `gpt-6-astra.md`.

To change one, copy it into your templates folder, keep the same file name, and edit the copy. Your file then replaces the bundled one, and workflow updates won't overwrite it.

Two placeholder lines are filled in from your settings and removed when the setting is blank:

- `{{ABOUT_USER}}` becomes "About the user: …"
- `{{MISHEARD_NAMES}}` becomes "Names that often come through wrong include …"

## Updating a model

The model IDs are listed at the top of `enhance.zsh` in the workflow folder. To point an action at a newer model, change its ID there. To add a model, add a line there, add a template named after the mode, and add a Universal Action that sets `ENHANCER_MODE` to that mode.

## Troubleshooting

- **A notification says a CLI isn't installed or signed in.** Follow the command it gives in Terminal, then try again.
- **The CLI is installed but not found.** Alfred runs with a minimal PATH. The workflow also asks your login shell. If it still can't find the CLI, add a `CLAUDE_BIN` or `CODEX_BIN` workflow environment variable with the full path (Alfred Preferences → Workflows → Prompt Enhancer → `[x]` button).
- **Logs.** Each run keeps a folder with the request, output and errors in Alfred's workflow cache (`~/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/net.spidleweb.prompt-enhancer/`). Only the 20 newest runs are kept, since each one includes the selected text.

## Build a release

```bash
./build.sh
```

This checks the workflow and writes `dist/Prompt-Enhancer-<version>.alfredworkflow`. The version comes from `workflow/info.plist`.

## License

MIT. See [LICENSE](LICENSE).
