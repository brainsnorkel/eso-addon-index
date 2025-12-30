# GitHub Proxy Options for ESO Addon Index

## Problem Statement

Clients (addon managers) need to access GitHub for:
1. **Release metadata** - Version info, release dates, changelogs
2. **Download URLs** - Archive files for installation
3. **Repository info** - Branch HEAD commits for branch-tracked addons

Current challenges:
- **Rate limiting**: GitHub API allows 60 req/hour unauthenticated, 5000/hour with token
- **CORS restrictions**: Browser-based clients can't call GitHub API directly
- **Stale URLs**: Pre-computed download URLs in index.json can become invalid
- **Availability**: GitHub outages affect all clients

---

## Option 1: Enhanced Static Index (Current + Improvements)

**Approach**: Build script pre-fetches all data, embeds in index.json

```json
{
  "latest_release": {
    "version": "v1.3.0",
    "download_url": "https://github.com/.../v1.3.0.zip",
    "download_url_jsdelivr": "https://cdn.jsdelivr.net/gh/owner/repo@v1.3.0/",
    "published_at": "2024-12-01T12:00:00Z",
    "commit_sha": "abc123..."
  }
}
```

**Pros**:
- Zero runtime infrastructure
- Free (GitHub Pages)
- Simple client implementation

**Cons**:
- Data freshness depends on poll frequency (currently daily)
- No real-time updates
- Download URLs could 404 if releases deleted

**Verdict**: ✅ Good baseline, already implemented

---

## Option 2: jsDelivr CDN Integration

**Approach**: Use jsDelivr as a free GitHub proxy/CDN

jsDelivr already provides:
- `https://cdn.jsdelivr.net/gh/owner/repo@version/path` - Tagged releases
- `https://cdn.jsdelivr.net/gh/owner/repo@branch/path` - Branch HEAD
- Automatic caching, global CDN, no rate limits

**Implementation**:
```json
{
  "install": {
    "method": "jsdelivr",
    "jsdelivr_url": "https://cdn.jsdelivr.net/gh/nicokimmel/wizardswardrobe@v1.18.2/src/",
    "fallback_url": "https://github.com/..."
  }
}
```

**Pros**:
- Free, fast, reliable CDN
- No rate limits
- CORS-friendly
- Automatic cache invalidation on new releases

**Cons**:
- Third-party dependency
- 50MB file size limit
- May have slight delay on new releases (~24hr cache)

**Verdict**: ✅ Excellent option for downloads, should add as primary/fallback

---

## Option 3: Cloudflare Workers Proxy

**Approach**: Lightweight edge function that proxies GitHub API

```
https://eso-addon-index.workers.dev/api/repos/{owner}/{repo}/releases/latest
```

**Implementation**:
```javascript
// Cloudflare Worker
export default {
  async fetch(request) {
    const cache = caches.default;
    const cached = await cache.match(request);
    if (cached) return cached;

    const response = await fetch(`https://api.github.com${path}`, {
      headers: { 'Authorization': `token ${GITHUB_TOKEN}` }
    });

    const clone = response.clone();
    clone.headers.set('Cache-Control', 'max-age=300'); // 5 min cache
    await cache.put(request, clone);
    return response;
  }
}
```

**Pros**:
- Real-time data with caching
- Bypasses client rate limits (uses server token)
- CORS headers configurable
- 100k free requests/day

**Cons**:
- Requires Cloudflare account
- Token management (security concern)
- More complex deployment

**Verdict**: ⚠️ Good for API proxying, overkill for current needs

---

## Option 4: GitHub Actions Artifact Proxy

**Approach**: Cache release archives in GitHub Actions artifacts or Pages

```yaml
# .github/workflows/cache-releases.yml
- name: Download and cache releases
  run: |
    for addon in addons/*/addon.toml; do
      # Download release archive
      # Store in public/releases/{slug}/{version}.zip
    done
```

**Pros**:
- Full control over cached files
- No external dependencies
- Can serve even if original repo deleted

**Cons**:
- Storage limits (1GB for Pages, 500MB artifacts)
- Bandwidth costs at scale
- Legal considerations (redistributing code)

**Verdict**: ❌ Storage/legal concerns make this impractical

---

## Option 5: Hybrid Metadata + Direct Download

**Approach**: Proxy only metadata, let clients download directly from GitHub

```
Index Site (static)          GitHub
     │                          │
     ├─ index.json ◄────────────┤ (built daily)
     │   └─ download_url ───────►│
     │                          │
Client                         │
     ├─ GET index.json ◄────────┤
     └─ GET download_url ───────►│ (direct to GitHub)
```

**This is essentially the current architecture**, but we can enhance it:

1. **Multiple download sources**: GitHub, jsDelivr, GitLab mirrors
2. **Fallback chain**: Client tries sources in order
3. **Health status**: Index includes source availability

```json
{
  "download_sources": [
    {"type": "jsdelivr", "url": "https://cdn.jsdelivr.net/gh/..."},
    {"type": "github_archive", "url": "https://github.com/.../archive/..."},
    {"type": "github_release", "url": "https://github.com/.../releases/..."}
  ]
}
```

**Verdict**: ✅ Best practical approach

---

## Recommendation

### Immediate (No infrastructure changes)

1. **Add jsDelivr URLs** to index.json as primary download source
2. **Keep GitHub URLs** as fallback
3. **Document fallback behavior** in client integration guide

### Build script changes:

```python
def generate_download_sources(addon):
    sources = []

    # Primary: jsDelivr (cached, fast, CORS-friendly)
    if addon.release_type == "tag":
        sources.append({
            "type": "jsdelivr",
            "url": f"https://cdn.jsdelivr.net/gh/{addon.repo}@{addon.version}/"
        })

    # Fallback: GitHub archive
    sources.append({
        "type": "github_archive",
        "url": f"https://github.com/{addon.repo}/archive/refs/tags/{addon.version}.zip"
    })

    return sources
```

### Future (If needed)

- Cloudflare Worker for real-time API access
- Consider Deno Deploy or Vercel Edge as alternatives

---

## Client Implementation Notes

Recommended client download logic:

```python
async def download_addon(addon):
    for source in addon.download_sources:
        try:
            if source.type == "jsdelivr":
                # jsDelivr serves directory listings, need to fetch files
                return await download_jsdelivr(source.url, addon.install.target_folder)
            elif source.type == "github_archive":
                return await download_and_extract_zip(source.url)
        except DownloadError:
            continue  # Try next source
    raise AllSourcesFailedError()
```

---

## Open Questions

1. **jsDelivr rate limits**: Need to verify no hidden limits for high-traffic use
2. **Archive structure**: jsDelivr serves files individually vs zip - client complexity
3. **Branch tracking**: jsDelivr caches branch HEAD, may be delayed
4. **License implications**: Ensure redistribution via CDN is permitted

---

## References

- [jsDelivr GitHub Integration](https://www.jsdelivr.com/github)
- [GitHub API Rate Limits](https://docs.github.com/en/rest/rate-limit)
- [Cloudflare Workers](https://workers.cloudflare.com/)
