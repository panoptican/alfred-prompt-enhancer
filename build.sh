#!/bin/zsh
# Build dist/Prompt-Enhancer-<version>.alfredworkflow from workflow/.
# The version comes from workflow/info.plist.
set -euo pipefail

root="${0:A:h}"
wf="$root/workflow"

plutil -lint -s "$wf/info.plist"
zsh -n "$wf/enhance.zsh"

# Script, template and action modes must match in both directions.
script_modes=( ${(f)"$(grep -oE '^PROVIDER\[[^]]+\]' "$wf/enhance.zsh" | sed -E 's/^PROVIDER\[(.*)\]$/\1/')"} )
action_modes=( ${(f)"$(plutil -convert json -o - "$wf/info.plist" | grep -oE '"ENHANCER_MODE":"[^"]+"' | cut -d'"' -f4)"} )
for mode in $script_modes; do
  [[ -f "$wf/templates/$mode.md" && -r "$wf/templates/$mode.md" ]] || { print -u2 "Missing template: templates/$mode.md"; exit 1; }
  (( ${action_modes[(Ie)$mode]} )) || { print -u2 "Missing action for mode: $mode"; exit 1; }
done
for mode in $action_modes; do
  (( ${script_modes[(Ie)$mode]} )) || { print -u2 "Action uses unknown mode: $mode"; exit 1; }
done

for template in "$wf"/templates/*.md(N); do
  mode="${template:t:r}"
  (( ${script_modes[(Ie)$mode]} )) || { print -u2 "Template uses unknown mode: $mode"; exit 1; }
done

version="$(/usr/libexec/PlistBuddy -c 'Print :version' "$wf/info.plist")"
mkdir -p "$root/dist"
out="$root/dist/Prompt-Enhancer-$version.alfredworkflow"
rm -f "$out"
# A .alfredworkflow file is a zip of the workflow folder. Leave out dotfiles and backups.
(cd "$wf" && zip -q -r -X "$out" . -x '.*' '*/.*' '*.bak*')

print "Built $out (${#script_modes} modes, ${#action_modes} actions)"
