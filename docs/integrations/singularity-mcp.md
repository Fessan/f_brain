# Singularity MCP Integration (Iteration 1)

This project can use Singularity App through MCP in the `claude-cli` provider path.

## Prerequisites

- Singularity account with MCP/API access
- A token from `https://me.singularity-app.com/rest-tokens`
- Claude CLI login completed in container (`make claude-auth`)

## Step 1: Download MCP configuration from Singularity

1. Open `https://me.singularity-app.com/mcp`
2. Download MCP configuration bundle from your account
3. If needed, rename `.mcpb` to `.zip` and extract (per Singularity docs)
4. Place resulting config in project root, for example:

`mcp-config.singularity.json`

## Step 2: Ensure Todoist + Singularity are both configured

Your MCP config should contain both MCP servers if you want both integrations available.

- Keep existing `todoist` MCP server block
- Add the `singularity` MCP server block from your downloaded config

## Step 3: Configure environment

In `.env`:

- `TASK_BACKEND=singularity`
- `MCP_CONFIG_PATH=mcp-config.singularity.json`
- `SINGULARITY_API_KEY=<your token>` (if required by your MCP server)

`MCP_CONFIG_PATH` is resolved relative to project root.

## Step 4: Restart services

```bash
make down
make up
make logs
```

## Step 5: Verify in Telegram

Run a `/do` request that should touch Singularity tasks. Then inspect bot logs for MCP tool calls/errors.

## Notes

- Current iteration focuses on MCP path (`claude-cli`) integration.
- `openai-api` provider capability parity for Singularity is planned for next iteration.
