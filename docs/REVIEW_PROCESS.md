# Addon Review Process

This document outlines the review process for addon submissions.

## Automated Checks

Every PR triggers automated validation:

### 1. TOML Schema Validation
- Valid TOML syntax
- Required fields present
- Field types correct
- Slug matches directory name

### 2. Repository Validation
- Repository exists and is accessible
- Contains ESO addon manifest (`.txt` with `## Title:`)
- Has at least one release or tag

### 3. Luacheck Analysis
- Static analysis of Lua code
- Errors block the PR
- Warnings are noted but don't block

### 4. Security Scan
Flags suspicious patterns:
- `os.execute` / `io.popen` (shell commands)
- `loadstring` / `load` (dynamic code execution)
- `dofile` / `loadfile` (external file loading)

## Manual Review Checklist

Reviewers should verify:

### Repository Check
- [ ] Repository is genuine (not a fork of unrelated project)
- [ ] Commit history looks legitimate
- [ ] Author matches addon credits

### Code Review
- [ ] No obvious malicious code
- [ ] No data exfiltration
- [ ] No unauthorized network calls
- [ ] Reasonable addon functionality

### Metadata Accuracy
- [ ] Name matches addon
- [ ] Description is accurate
- [ ] Category is appropriate
- [ ] Tags are relevant
- [ ] License is correct

### Quality Standards
- [ ] Not a duplicate of existing addon
- [ ] Provides useful functionality
- [ ] Reasonably maintained

## Review Workflow

```
PR Opened
    │
    ▼
Automated Checks ───────► Fail ───► Request Changes
    │
    │ Pass
    ▼
Manual Review ──────────► Issues ──► Request Changes
    │
    │ Approved
    ▼
Merge to Main
    │
    ▼
Auto-Deploy to GitHub Pages
```

## Reviewer Commands

In PR comments:

- `/approve` - Approve the submission
- `/request-changes` - Request changes (explain in comment)
- `/security-concern` - Flag for security review
- `/duplicate [slug]` - Mark as duplicate of existing addon

## Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Awaiting initial review |
| `approved` | Active in the index |
| `deprecated` | Still listed but no longer maintained |
| `removed` | Removed from index (violation/request) |

## Escalation

Security concerns should be:
1. Flagged immediately with `/security-concern`
2. Discussed privately with maintainers
3. Not publicly disclosed until resolved

## Time Expectations

- Automated checks: ~2 minutes
- Initial review: Within 48 hours
- Follow-up reviews: Within 24 hours

## Becoming a Reviewer

Interested in helping review submissions?

1. Be an active ESO addon user/developer
2. Demonstrate understanding of ESO addon security
3. Contact maintainers via issue or discussion
