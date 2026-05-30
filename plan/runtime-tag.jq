# Map each manifest matrix row's runtime to a flathub-infra builder-container tag.
# The CLI stays runtime-agnostic; this GitHub/flathub naming lives in the actions
# layer. Verified tags (skopeo list-tags, 2026-05-30): freedesktop-*, gnome-*,
# kde-*. No elementary-* (or other) tag is published.
#
# Per row:
#   reverse-DNS runtime in the allowlist -> "<prefix>-<runtime-version>"
#   value already a flathub tag (config mode, no dot) -> passthrough
#   anything else -> error (fails the step)
def runtime_tag:
  {
    "org.freedesktop.Platform": "freedesktop",
    "org.gnome.Platform":       "gnome",
    "org.kde.Platform":         "kde"
  } as $allow
  | .runtime as $r
  | if $allow[$r] then
      ($allow[$r] + "-"
        + (."runtime-version"
           // error("manifest runtime '\($r)' is missing runtime-version")))
    elif ($r | test("[.]") | not) then
      $r
    else
      error("unsupported runtime '\($r)'; supported: org.freedesktop.Platform, org.gnome.Platform, org.kde.Platform")
    end;
[ .[] | . + {"runtime-tag": runtime_tag} ]
