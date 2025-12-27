# Registry Architecture Considerations

## Background

Reference: [Package managers keep using git as a database](https://nesbitt.io/2025/12/24/package-managers-keep-using-git-as-a-database.html)

This document explores architectural patterns for package registries based on lessons learned from major package managers that have scaled beyond git-as-database approaches.

---

## Current Architecture

The ESO addon index currently uses:
- **TOML files in git** for addon metadata (`addons/[slug]/addon.toml`)
- **GitHub Actions** to compile TOML to JSON on push
- **GitHub Pages** to serve static JSON (`index.json`)

This is the classic "git as database" pattern that several major registries have moved away from.

---

## Case Studies from the Article

### Cargo (Rust) - crates.io

**Problem:** Full index clone required by all users, causing delta resolution delays.

**Solution:** Sparse HTTP protocol (RFC 2789) - fetch only needed metadata rather than full repository.

**Relevance:** If ESO addon index grows significantly, users/tools fetching the full `index.json` may face similar issues.

### Homebrew

**Problem:** GitHub explicitly requested they stop shallow clones due to expensive operations. Users downloading 331MB+ just to update.

**Solution:** Migrated to JSON downloads running every 24 hours instead of every 5 minutes via git.

**Relevance:** Our current approach (static JSON via GitHub Pages) is similar to Homebrew's solution. This is good.

### CocoaPods

**Problem:** Specs repository with hundreds of thousands of entries became unwieldy.

**Quote:** "Git was invented at a time when 'slow network' and 'no backups' were legitimate design concerns."

**Solution:** Abandoned git entirely for a CDN-based approach.

**Relevance:** At scale, individual addon directories may cause filesystem issues.

### vcpkg

**Problem:** Deeply coupled to git with no escape plan. Tree hashes require full commit history.

**Relevance:** Warning against tight coupling to git internals.

---

## Underlying Problems Identified

1. **Directory constraints** - slowness with too many files
2. **Case sensitivity** - conflicts between platforms
3. **Path length limits** - Windows issues
4. **Missing database features** - no constraints, locking, indexing

---

## Current Mitigations (Already Implemented)

| Risk | Mitigation |
|------|------------|
| Full clone required | Static JSON served via GitHub Pages (no git clone needed by consumers) |
| Large directory counts | Flat structure under `addons/` |
| CI clone overhead | Only metadata, not source code |

---

## Potential Future Improvements

### Tier 1: Easy Wins (Current Scale)

- [x] Static JSON via GitHub Pages (already done)
- [ ] Add `index.min.json` for bandwidth optimization
- [ ] Add `feed.json` (JSON Feed) for update notifications
- [ ] Consider gzip/brotli compression headers

### Tier 2: Medium Scale (~500+ addons)

- [ ] Split index by category (`combat.json`, `ui.json`, etc.)
- [ ] Add sparse endpoint per addon (`/addons/warmask.json`)
- [ ] Implement ETag/Last-Modified headers for caching
- [ ] Consider CDN (Cloudflare Pages, Netlify) instead of GitHub Pages

### Tier 3: Large Scale (~5000+ addons)

- [ ] SQLite database with JSON export
- [ ] Full sparse protocol (fetch only needed metadata)
- [ ] Search API endpoint
- [ ] Consider serverless functions for dynamic queries

---

## Key Insight

> The article recommends avoiding git-as-database entirely. Our current architecture is a **hybrid approach**:
> - Git for **source of truth** (TOML files, PR workflow, review process)
> - Static JSON for **consumption** (no git required by clients)
>
> This is similar to Homebrew's evolved solution and should scale reasonably well.

---

## Decision

For now, the current architecture is appropriate because:

1. ESO addon ecosystem is relatively small (~1000 addons total on ESOUI)
2. Only curated/reviewed addons will be included (subset of total)
3. Static JSON approach avoids git clone requirement for consumers
4. GitHub Pages provides free, reliable CDN

**Revisit this document if:**
- Index exceeds 500 addons
- GitHub Pages bandwidth becomes an issue
- Users report slow index fetch times

---

## References

- [Cargo Sparse Protocol RFC 2789](https://rust-lang.github.io/rfcs/2789-sparse-index.html)
- [Homebrew Migration Discussion](https://github.com/Homebrew/brew/issues/9359)
- [CocoaPods CDN](https://blog.cocoapods.org/CocoaPods-1.7.2/)
- [Original Article](https://nesbitt.io/2025/12/24/package-managers-keep-using-git-as-a-database.html)
