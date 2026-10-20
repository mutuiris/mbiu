# Data transfers

Under Kenya's Data Protection Act, every provider that receives contract text is a cross-border transfer. This list must match the privacy notice and the actual provider settings.

| Provider | Receives | Storage setting | Retention | Tier |
|---|---|---|---|---|
| Google Gemini API | Clause text, linked clauses, template excerpts, follow-up questions | Interactions API with `store=False`; AI Studio logging off | Not stored for the app. Google keeps logs for a limited period for abuse monitoring and legal requirements | Paid only |
| OpenAI API (failover only, off by default) | Same as Gemini, only when Gemini is unavailable | `store: false` on every call | To confirm against OpenAI's data controls before failover is enabled | Paid only |

Providers that receive no contract text:

- **Supabase:** public templates, statutes and guidance only.
- **Vercel:** serves the web app. Contract files go from the browser straight to the API.
- **Grafana Cloud, Sentry, PostHog:** counts, IDs, durations, error categories and versions only.
- **Cloudflare Turnstile:** bot-check token only.
