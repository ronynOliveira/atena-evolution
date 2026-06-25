import shutil

yaml_content = """api_timeout: 300
cache_ttl: 900
gateway_timeout: 3600
mcp_servers:
    google-search:
        args:
            - C:\\Users\\dell-\\AppData\\Local\\hermes\\tools\\google-search\\dist\\src\\mcp-server.js
        command: node
        connect_timeout: 30
        timeout: 120
    google-workspace:
        command: workspace-mcp
        args:
            - --single-user
            - --tools
            - gmail
            - calendar
            - drive
            - docs
            - sheets
            - slides
            - tasks
            - --transport
            - stdio
        connect_timeout: 60
        timeout: 120
model:
    api_key_env: OPENROUTER_API_KEY
    api_max_retries: 5
    base_url: https://openrouter.ai/api/v1
    default: openrouter/owl-alpha
    fallback_providers:
        - model: deepseek/deepseek-v4-flash:free
          provider: openrouter
        - model: google/gemini-3.1-flash-lite
          provider: openrouter
    provider: openrouter
    rate_limit_backoff_base: 5
    rate_limit_backoff_max: 120
plugins:
    enabled:
        - koldi-computer-use
        - koldi-browser
providers:
    google:
        api: https://generativelanguage.googleapis.com/v1beta/openai/
        api_key_env: GOOGLE_API_KEY
        default_model: google/gemini-1.5-flash
        models:
            - google/gemini-1.5-flash
            - google/gemini-1.5-pro
        name: Google AI Studio
    openrouter:
        api: https://openrouter.ai/api/v1
        api_key_env: OPENROUTER_API_KEY
        default_model: openrouter/owl-alpha
        models:
            - openrouter/owl-alpha
            - deepseek/deepseek-v4-flash:free
            - google/gemini-3.1-flash-lite
        name: OpenRouter
response_cache_ttl: 1200
toolsets:
    - hermes-cli
    - web
user_char_limit: 20000

approvals:
  mode: manual
  timeout: 60
  cron_mode: deny
  mcp_reload_confirm: true
  destructive_slash_confirm: true

network:
  allow_private_network_access: false

memory:
  auto_ingest: false
  require_confirmation: true
  trusted_sources:
    - cli

compression:
  enabled: true
  threshold: 0.4
  protect_last_n: 10

security:
  privacy:
    redact_pii: true
"""

dst = r"C:\Users\dell-\.hermes\config.yaml"
with open(dst, "w", encoding="utf-8") as f:
    f.write(yaml_content)
print(f"Written to {dst}: {len(yaml_content)} chars")

# Verify
with open(dst, "r", encoding="utf-8") as f:
    content = f.read()
print(f"Verify: {len(content)} chars read back")
print("First 5 lines:")
for i, line in enumerate(content.split("\n")[:5], 1):
    print(f"  {i}: {line}")