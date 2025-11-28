# Custom Slash Command Plan: `/agent-summary`

## Overview
Create a `/agent-summary` slash command for Amp and Claude Code that provides intelligent summaries of recent dev-agent findings, tailored to the current development context.

---

## 1. Command Design

### Command Syntax
```bash
/agent-summary [scope] [filters]
```

### Parameters
- `scope`: `recent` (default), `today`, `session`, `all`
- `filters`: `--agent=<name>`, `--severity=<level>`, `--category=<type>`

### Examples
```bash
/agent-summary                    # Recent findings summary
/agent-summary today              # Today's findings
/agent-summary --agent=linter     # Only linter findings
/agent-summary recent --severity=error  # Recent errors only
```

---

## 2. Implementation Architecture

### A. Summary Generator Module
```python
# src/dev_agents/core/summary_generator.py
class SummaryGenerator:
    def __init__(self, context_store):
        self.context_store = context_store
    
    async def generate_summary(
        self, 
        scope: str = "recent",
        filters: Dict[str, Any] = None
    ) -> SummaryReport:
        """Generate intelligent summary of findings."""
        pass
    
    def _filter_findings(self, findings: List[Finding], filters: Dict) -> List[Finding]:
        """Apply user-specified filters."""
        pass
    
    def _group_by_agent(self, findings: List[Finding]) -> Dict[str, List[Finding]]:
        """Group findings by agent type."""
        pass
    
    def _calculate_trends(self, findings: List[Finding]) -> Dict[str, Any]:
        """Calculate improvement/worsening trends."""
        pass
```

### B. CLI Integration
```python
# src/dev_agents/cli/commands/summary.py
@app.command()
def agent_summary(
    scope: str = typer.Argument("recent", help="Summary scope: recent|today|session|all"),
    agent: str = typer.Option(None, help="Filter by agent name"),
    severity: str = typer.Option(None, help="Filter by severity"),
    category: str = typer.Option(None, help="Filter by category")
):
    """Generate intelligent summary of dev-agent findings."""
    import asyncio
    from dev_agents.core.summary_generator import SummaryGenerator
    
    filters = {}
    if agent:
        filters["agent"] = agent
    if severity:
        filters["severity"] = severity
    if category:
        filters["category"] = category
    
    generator = SummaryGenerator(context_store)
    result = asyncio.run(generator.generate_summary(scope, filters))
    
    console.print(SummaryFormatter.format(result))
```

### C. Amp/Claude Code Integration
```python
# src/dev_agents/core/amp_integration.py
async def generate_agent_summary(
    scope: str = "recent", 
    filters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Generate summary report for Amp/Claude Code slash command."""
    generator = SummaryGenerator(context_store)
    summary = await generator.generate_summary(scope, filters)
    
    return {
        "summary": summary.to_dict(),
        "formatted_report": SummaryFormatter.format_markdown(summary),
        "quick_stats": summary.get_quick_stats()
    }
```

---

## 3. Summary Report Structure

### Data Classes
```python
@dataclass
class SummaryReport:
    """Comprehensive summary report."""
    
    scope: str
    time_range: Tuple[datetime, datetime]
    total_findings: int
    
    # Breakdowns
    by_agent: Dict[str, AgentSummary]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    
    # Trends
    trends: Dict[str, Any]
    
    # Priority items
    critical_issues: List[Finding]
    auto_fixable: List[Finding]
    
    # Insights
    insights: List[str]

@dataclass
class AgentSummary:
    """Summary for a specific agent."""
    
    agent_name: str
    finding_count: int
    severity_breakdown: Dict[str, int]
    top_issues: List[Finding]
    improvement_trend: str  # "improving", "worsening", "stable"
```

---

## 4. Intelligence Features

### A. Contextual Awareness
- **Current File Focus**: Prioritize findings in currently edited files
- **Recent Changes**: Highlight issues related to recently modified files  
- **Development Phase**: Adapt summary based on coding vs. review phase

### B. Trend Analysis
- **Improvement Tracking**: "Issues decreased by 30% since yesterday"
- **Problematic Areas**: "Most issues in authentication module"
- **Agent Effectiveness**: "Linter caught 15 potential bugs today"

### C. Actionable Insights
- **Quick Fixes**: "5 auto-fixable issues ready to apply"
- **Blocking Issues**: "2 critical errors need immediate attention"
- **Patterns**: "Consistent style issues in new files"

---

## 5. Output Formats

### A. Markdown Report (for Claude Code)
```markdown
## 🔍 Dev-Agent Summary (Last 24h)

### 📊 Quick Stats
- **Total Findings:** 23
- **Critical Issues:** 2  
- **Auto-fixable:** 8
- **Trend:** 📈 Improving (↓15% from yesterday)

### 🚨 Priority Issues
1. **Security**: SQL injection vulnerability in `auth.py:42`
2. **Performance**: Memory leak in `cache.py:156`

### 📈 Agent Performance
- **Linter**: 12 findings (8 style, 3 warnings, 1 error)
- **Security**: 5 findings (2 critical, 3 medium)  
- **Type Checker**: 6 findings (all low priority)

### 💡 Insights
- Most issues are in the authentication module
- 3 new contributors need style guide review
- Security posture improved by 25% this week

### 🛠️ Quick Actions
Run `/agent-fix` to apply 8 safe fixes automatically
```

### B. JSON API (for Amp integration)
```json
{
  "summary": {
    "scope": "recent",
    "total_findings": 23,
    "critical_count": 2,
    "auto_fixable_count": 8,
    "trend": "improving",
    "trend_percentage": -15
  },
  "by_agent": {
    "linter": {"count": 12, "critical": 1, "auto_fixable": 5},
    "security": {"count": 5, "critical": 2, "auto_fixable": 2},
    "type_checker": {"count": 6, "critical": 0, "auto_fixable": 1}
  },
  "insights": [
    "Most issues in authentication module",
    "New contributors need style guide review", 
    "Security improved by 25% this week"
  ]
}
```

---

## 6. Integration Points

### A. Amp Slash Command
```typescript
// Amp extension
registerSlashCommand({
  name: "agent-summary",
  description: "Get summary of recent dev-agent findings",
  handler: async (args) => {
    const result = await callDevAgentsAPI("agent-summary", args);
    return formatAmpResponse(result);
  }
});
```

### B. Claude Code Integration
```python
# In Claude Code extension
def handle_slash_command(command, args):
    if command == "agent-summary":
        result = subprocess.run(
            ["dev-agents", "agent-summary"] + args, 
            capture_output=True, 
            text=True
        )
        return format_markdown_response(result.stdout)
```

---

## 7. Implementation Timeline

### Phase 1: Core Infrastructure (1-2 days)
- [ ] Create `SummaryGenerator` class
- [ ] Implement basic filtering and grouping
- [ ] Add CLI command skeleton
- [ ] Basic markdown output

### Phase 2: Intelligence Features (2-3 days)  
- [ ] Add trend analysis
- [ ] Implement contextual awareness
- [ ] Create actionable insights
- [ ] Enhanced filtering options

### Phase 3: Amp/Claude Integration (1-2 days)
- [ ] Amp slash command implementation
- [ ] Claude Code integration
- [ ] JSON API endpoints
- [ ] Testing and refinement

### Phase 4: Advanced Features (2-3 days)
- [ ] Machine learning insights
- [ ] Custom report templates  
- [ ] Historical trend analysis
- [ ] Performance optimizations

---

## 8. Success Metrics

- **Adoption**: Used in 80% of development sessions
- **Time Savings**: Reduces issue discovery time by 50%
- **User Satisfaction**: 4.5+ star rating from developers
- **Integration**: Seamless experience in both Amp and Claude Code

---

## 9. Testing Strategy

### Unit Tests
- Summary generation accuracy
- Filtering logic correctness
- Trend calculation validation
- Output formatting verification

### Integration Tests
- End-to-end CLI command testing
- Amp/Claude Code integration
- Real finding data processing

### User Acceptance Tests
- Developer workflow integration
- Summary relevance and usefulness
- Performance impact assessment

---

## 10. Future Enhancements

- **Custom Dashboards**: Web-based summary visualization
- **Team Analytics**: Cross-developer trend analysis
- **Predictive Insights**: ML-based issue prediction
- **Automated Reports**: Scheduled summary emails
- **Integration APIs**: REST/webhook interfaces

---

## Files to Create/Modify:
- `src/dev_agents/core/summary_generator.py` - Core summary logic
- `src/dev_agents/cli/commands/summary.py` - CLI command
- `src/dev_agents/core/amp_integration.py` - Amp/Claude integration
- `tests/unit/core/test_summary_generator.py` - Unit tests
- `AGENTS.md` - Update with new feature documentation

**Ready to implement! 🚀**
