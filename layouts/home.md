{{/*

Markdown output for the home page.

Extends the generic all.md template by injecting the site.Params.home tile
data as a "Getting started" section between the description/llms links and
the section page list. The tile data is the same source used by the HTML
homepage template, so agents see equivalent content.

*/ -}}

# {{ .Title | strings.TrimSpace -}}

{{ $includeLlmsIndex := true -}}
{{ $needSeparator := false -}}

{{/* Description ------------------------------------------------------- */ -}}

{{ with .Description | strings.TrimSpace }}

> {{ replace . "\n" "\n> " -}}
{{ $needSeparator = true -}}
{{ end -}}

{{/* Site index -------------------------------------------------------- */ -}}

{{ if $includeLlmsIndex }}
{{ if $needSeparator }}
---

{{ else }}
{{ end -}}

{{ $llmsTxt := "llms.txt" -}}
{{ $llmsFullTxt := "llms-full.txt" -}}
LLMS index: [ {{- $llmsTxt -}} ]( {{- $llmsTxt | relURL -}} ) | Full content: [ {{- $llmsFullTxt -}} ]( {{- $llmsFullTxt | relURL -}} )
{{ $needSeparator = true -}}
{{ end -}}

{{/* Page content ------------------------------------------------------ */ -}}

{{ with .RenderShortcodes | strings.TrimSpace -}}
{{ if $needSeparator }}
---

{{ else }}
{{ end -}}

{{ . }}
{{ $needSeparator = true -}}
{{ end -}}

{{/* Getting started tiles --------------------------------------------- */ -}}

{{ with .Site.Params.home -}}
{{ if $needSeparator }}
---

{{ end -}}
## Getting started

{{ range . -}}
- **[{{ .title }}]({{ .url }})**: {{ .url_text }}
{{ end -}}
{{ $needSeparator = true -}}
{{ end -}}

{{/* Section index, if any --------------------------------------------- */ -}}

{{ with .Pages -}}

{{ if $needSeparator }}
---

{{ else }}
{{ end -}}

Section pages:

{{ range . -}}
- [ {{- .Title | strings.TrimSpace -}} ]( {{- .RelPermalink -}} )
  {{- with .Description | strings.TrimSpace -}}
  : {{ . -}}
  {{ end }}
{{ end -}}

{{ end -}}
