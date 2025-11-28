# DevLoop Roadmap

Future plans and feature development for DevLoop.

---

## Current Version: 0.2.0

**Status:** Production ready with Phase 1, 2, and 3 complete

**Latest:** Project renamed from dev-agents to DevLoop

---

## Planned Features

### Multi-CI Platform Support 🚀 **High Priority**

**Current State:** GitHub Actions only (via `gh` CLI)

**Goal:** Support all major CI/CD platforms with unified interface

**Planned Platforms:**
1. ✅ **GitHub Actions** - Currently supported
2. 🔄 **GitLab CI/CD** - Next priority
   - Via `glab` CLI or GitLab API
   - Auto-detect `.gitlab-ci.yml`
3. 📋 **Jenkins**
   - Via Jenkins API
   - Auto-detect `Jenkinsfile`
4. 📋 **CircleCI**
   - Via CircleCI API
   - Auto-detect `.circleci/config.yml`
5. 📋 **Travis CI**
   - Via Travis API
   - Auto-detect `.travis.yml`
6. 📋 **Azure DevOps Pipelines**
   - Via Azure CLI
   - Auto-detect `azure-pipelines.yml`
7. 📋 **Bitbucket Pipelines**
   - Via Bitbucket API
   - Auto-detect `bitbucket-pipelines.yml`
8. 📋 **Generic CI/CD**
   - Configurable webhook/API support
   - Custom status endpoints

**Implementation Plan:**
- [ ] Design pluggable CI adapter interface
- [ ] Create CI provider auto-detection
- [ ] Implement GitLab adapter (first alternative platform)
- [ ] Add provider configuration to `.devloop/agents.json`
- [ ] Create adapter for each major platform
- [ ] Add comprehensive testing for all adapters
- [ ] Document setup for each platform

**Design Pattern:**
```python
class CIAdapter(ABC):
    @abstractmethod
    def check_status(self, branch: str) -> CIStatus:
        """Check CI status for branch."""

    @abstractmethod
    def get_latest_run(self, branch: str) -> Optional[CIRun]:
        """Get latest CI run for branch."""

# Implementations
GitHubCIAdapter(CIAdapter)  # Current
GitLabCIAdapter(CIAdapter)  # Next
JenkinsCIAdapter(CIAdapter)
# etc.
```

**Configuration:**
```json
{
  "ci-monitor": {
    "config": {
      "provider": "auto",  // auto-detect or specify
      "providers": {
        "github": { "enabled": true },
        "gitlab": {
          "enabled": true,
          "url": "https://gitlab.com",
          "token_env": "GITLAB_TOKEN"
        },
        "jenkins": {
          "enabled": true,
          "url": "https://jenkins.example.com",
          "username_env": "JENKINS_USER",
          "token_env": "JENKINS_TOKEN"
        }
      }
    }
  }
}
```

**Why This Matters:**
- DevLoop should work with ANY project, not just GitHub-hosted ones
- Many enterprises use GitLab, Jenkins, or Azure DevOps
- Open source projects may use various CI platforms
- Consistent experience across all CI systems

---

## Other Planned Features

### Agent Enhancements

#### Custom Agent Builder UI 🎨
- Web-based or CLI tool to create custom agents
- Template library for common agent patterns
- No-code agent creation

#### Agent Marketplace 📦
- Share custom agents with community
- Install agents from central repository
- Rating and review system

#### Multi-Language Support 🌍
- JavaScript/TypeScript agent support
- Go agent support
- Rust agent support

### Integration Improvements

#### IDE Integration 💻
- VSCode extension
- JetBrains plugin
- Neovim plugin

#### Cloud Features ☁️
- Optional cloud sync for findings
- Team collaboration features
- Shared agent configurations

#### Notification Systems 📬
- Slack integration
- Discord webhooks
- Email notifications
- Desktop notifications

### Performance & Scalability

#### Optimization 🚀
- Parallel agent execution
- Incremental analysis (only changed files)
- Caching layer for agent results
- Resource usage optimization

#### Monorepo Support 📁
- Multi-project detection
- Workspace-aware agents
- Shared configuration inheritance

---

## Version Planning

### v0.3.0 - CI Platform Support (Q1 2025)
- GitLab CI/CD support
- Jenkins support
- Pluggable CI adapter system
- Provider auto-detection

### v0.4.0 - IDE Integration (Q2 2025)
- VSCode extension
- Real-time agent feedback in editor
- Inline quick fixes

### v0.5.0 - Agent Marketplace (Q2 2025)
- Custom agent sharing
- Agent discovery
- Installation system

### v1.0.0 - Production Release (Q3 2025)
- All major CI platforms supported
- IDE integrations stable
- Comprehensive documentation
- Production-tested at scale

---

## Contributing

Want to help build these features?

1. **Pick a feature** from this roadmap
2. **Open an issue** to discuss implementation
3. **Submit a PR** with your contribution

**High-impact contributions needed:**
- GitLab CI adapter implementation
- VSCode extension development
- Documentation improvements
- Testing and bug reports

---

## Feedback

Have ideas for DevLoop? [Open an issue](https://github.com/wioota/devloop/issues) or start a [discussion](https://github.com/wioota/devloop/discussions).

---

**Legend:**
- ✅ Completed
- 🔄 In Progress
- 📋 Planned
- 🚀 High Priority
- 🎨 Nice to Have
- ☁️ Future Consideration
