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
LLMS index: [ {{- $llmsTxt -}} ]( {{- $llmsTxt | absURL -}} ) | Full content: [ {{- $llmsFullTxt -}} ]( {{- $llmsFullTxt | absURL -}} )
{{ $needSeparator = true -}}
{{ end -}}

{{/* Page content ------------------------------------------------------ */ -}}

{{ $pageContent := .RenderShortcodes | strings.TrimSpace -}}
{{ $pageContent = partial "resolve-md-links.txt" (dict "page" . "content" $pageContent) -}}
{{ with $pageContent -}}
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
- **[{{ .title }}]({{ .url | absURL }})**: {{ .url_text }}
{{ end -}}
{{ $needSeparator = true -}}
{{ end -}}

{{/* Section index, if any — skip when no_list is set in frontmatter ---- */ -}}

{{ if not .Params.no_list -}}
{{ with .Pages -}}

{{ if $needSeparator }}
---

{{ else }}
{{ end -}}

Section pages:

{{ range . -}}
- [ {{- .Title | strings.TrimSpace -}} ]( {{- .Permalink -}} )
  {{- with .Description | strings.TrimSpace -}}
  : {{ . -}}
  {{ end }}
{{ end -}}

{{ end -}}
{{ end -}}
