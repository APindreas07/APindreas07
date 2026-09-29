# Running the strategy lab in VS Code

## One-time setup
1. **Install the tools:**
   - VS Code;
   - Git;
   - Python 3.11 or newer;
   - the **Claude Code** extension. In VS Code, open Extensions, search "Claude Code" (publisher Anthropic),
     install it, then sign in with your claude.ai account.
2. **Get the code:**
   ```bash
   git clone https://github.com/APindreas07/APindreas07.git
   cd APindreas07
   git checkout claude/trades-log-returns-chart-1utamx
   code .
   ```
3. **Create a Python environment** in the VS Code terminal:
   ```bash
   python -m venv .venv
   # Windows:     .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r edge/lab/requirements.txt
   ```
4. **Check that everything works** by reproducing a finished study. It takes about 4 minutes and writes to
   `edge/fx2/results/`:
   ```bash
   python -m edge.fx2.research
   ```
5. **Connect TradeStation.** Open the Claude Code panel and type `/mcp`. The TradeStation connector from your
   claude.ai account should be listed. If it isn't, connect it at https://claude.ai/customize/connectors and
   reload VS Code.

## Run the loop
In the Claude Code panel, type:

```
/loop 4h Read edge/lab/AGENT.md and run exactly one strategy-lab round, following it strictly.
```

- One round runs every 4 hours, for as long as VS Code stays open and the computer stays awake.
- The loop stops when you close the panel or say "stop the loop".
- The agent commits and pushes to `claude/strategy-lab`, so your GitHub login in VS Code must have push access.

**Run only ONE lab loop at a time.** Before you start it locally, pause or delete the cloud routine
"FX strategy lab" (claude.ai, Routines). Otherwise two agents will write to the same branch and ledger.
