import { useState, useEffect } from 'react'
import { newsGetSites, newsAddSite, newsDeleteSite, newsGetArticles } from '../api'
import './NewsPanel.css'

// ── helpers ────────────────────────────────────────────────────────────────
function groupByState(sites) {
  return sites.reduce((acc, s) => {
    ;(acc[s.state] = acc[s.state] || []).push(s)
    return acc
  }, {})
}

function timeAgo(isoStr) {
  if (!isoStr) return null
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000
  if (diff < 60)    return 'just now'
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

// ══════════════════════════════════════════════════════════════════════════
// ADD SITE MODAL
// ══════════════════════════════════════════════════════════════════════════
function AddSiteModal({ availableDefaults, onAdd, onClose }) {
  const [tab, setTab]       = useState(availableDefaults.length > 0 ? 'defaults' : 'custom')
  const [state, setState]   = useState('')
  const [name, setName]     = useState('')
  const [url, setUrl]       = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError]   = useState('')

  async function handleAddDefault(d) {
    setAdding(true)
    setError('')
    try {
      await onAdd(d.state, d.name, d.url, d.id)
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setAdding(false)
    }
  }

  async function handleAddCustom(e) {
    e.preventDefault()
    if (!state.trim() || !name.trim() || !url.trim()) {
      setError('All fields are required.')
      return
    }
    try { new URL(url) } catch { setError('Please enter a valid URL.'); return }
    setAdding(true)
    setError('')
    try {
      await onAdd(state.trim(), name.trim(), url.trim(), null)
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="np-overlay" onClick={onClose}>
      <div className="np-modal" onClick={e => e.stopPropagation()}>
        <div className="np-modal-header">
          <span className="np-modal-title">Add News Source</span>
          <button className="np-modal-close" onClick={onClose}>×</button>
        </div>

        <div className="np-modal-tabs">
          <button className={`np-modal-tab${tab === 'defaults' ? ' active' : ''}`}
            onClick={() => setTab('defaults')}>Default Sources</button>
          <button className={`np-modal-tab${tab === 'custom' ? ' active' : ''}`}
            onClick={() => setTab('custom')}>Custom Site</button>
        </div>

        {error && <div className="np-modal-error">✗ {error}</div>}

        {tab === 'defaults' && (
          <div className="np-modal-body">
            {availableDefaults.length === 0 ? (
              <div className="np-modal-empty">All default sources are already in your list.</div>
            ) : (
              availableDefaults.map(d => (
                <div key={d.id} className="np-default-row">
                  <div>
                    <div className="np-default-name">{d.name}</div>
                    <div className="np-default-state">{d.state}</div>
                    <div className="np-default-url">{d.url}</div>
                  </div>
                  <button className="np-btn np-btn-add"
                    onClick={() => handleAddDefault(d)} disabled={adding}>
                    {adding ? '…' : '+ Add'}
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'custom' && (
          <form className="np-modal-body" onSubmit={handleAddCustom}>
            <label className="np-label">State / Region</label>
            <input className="np-input" placeholder="e.g. Kerala"
              value={state} onChange={e => setState(e.target.value)} />
            <label className="np-label">Site Name</label>
            <input className="np-input" placeholder="e.g. Mathrubhumi"
              value={name} onChange={e => setName(e.target.value)} />
            <label className="np-label">News URL</label>
            <input className="np-input" placeholder="https://example.com/politics"
              value={url} onChange={e => setUrl(e.target.value)} />
            <button type="submit" className="np-btn np-btn-primary" disabled={adding}>
              {adding ? 'Adding…' : '+ Add Site'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// ARTICLE VIEW
// ══════════════════════════════════════════════════════════════════════════
function ArticleView({ site, userId }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    setData(null)
    setLoading(true)
    setError(null)
    setExpanded(null)
    newsGetArticles(site.id, site.url, site.name)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [site.id])

  if (loading) return (
    <div className="np-articles-loading">
      <div className="np-spinner" />
      <div className="np-loading-title">Fetching articles…</div>
      <div className="np-loading-sub">
        Polling {site.url} and translating content. This may take up to a minute.
      </div>
    </div>
  )

  if (error) return (
    <div className="np-articles-error">
      <div className="np-error-icon">⚠</div>
      <div className="np-error-title">Could not fetch articles</div>
      <div className="np-error-msg">{error}</div>
    </div>
  )

  return (
    <div className="np-articles-wrap">
      <div className="np-articles-header">
        <div>
          <h2 className="np-articles-title">{site.name}</h2>
          <div className="np-articles-meta">
            {data?.from_cache
              ? <span className="np-cache-badge">Cached · polled {timeAgo(data.last_polled)}</span>
              : <span className="np-fresh-badge">Just fetched</span>}
            <a href={site.url} target="_blank" rel="noreferrer" className="np-source-link">
              {site.url} ↗
            </a>
          </div>
        </div>
      </div>

      {(!data?.articles || data.articles.length === 0) ? (
        <div className="np-articles-empty">
          <div>No articles could be extracted from this site.</div>
        </div>
      ) : (
        <div className="np-article-list">
          {data.articles.map((art, i) => (
            <div key={i} className={`np-article-card${expanded === i ? ' np-article-open' : ''}`}>
              {/* Collapsed: English title only */}
              <div className="np-article-top" onClick={() => setExpanded(expanded === i ? null : i)}>
                <span className="np-article-num">{i + 1}</span>
                <span className="np-article-headline">{art.title}</span>
                <span className="np-article-chevron">{expanded === i ? '▲' : '▼'}</span>
              </div>

              {/* Expanded: English content + original + link */}
              {expanded === i && (
                <div className="np-article-body">
                  {/* English translation */}
                  <p className="np-article-content">{art.content || 'No content extracted.'}</p>

                  {/* Original language section */}
                  {(art.title_original || art.content_original) && (
                    <div className="np-article-original">
                      <div className="np-original-label">Original</div>
                      {art.title_original && (
                        <p className="np-original-title">{art.title_original}</p>
                      )}
                      {art.content_original && (
                        <p className="np-original-content">{art.content_original}</p>
                      )}
                    </div>
                  )}

                  <a href={art.url} target="_blank" rel="noreferrer" className="np-article-src">
                    Read full article ↗
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// MAIN NEWS PANEL
// ══════════════════════════════════════════════════════════════════════════
export default function NewsPanel({ userId, onBack }) {
  const [sites, setSites]               = useState([])
  const [availableDefaults, setAvailableDefaults] = useState([])
  const [selected, setSelected]         = useState(null)   // site object
  const [showAdd, setShowAdd]           = useState(false)
  const [loading, setLoading]           = useState(true)
  const [deleteId, setDeleteId]         = useState(null)

  async function loadSites() {
    try {
      const data = await newsGetSites(userId)
      setSites(data.sites || [])
      setAvailableDefaults(data.available_defaults || [])
    } catch (e) {
      console.error('Failed to load sites', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadSites() }, [userId])

  async function handleAdd(state, name, url, siteId) {
    await newsAddSite(userId, state, name, url, siteId)
    await loadSites()
  }

  async function handleDelete(site) {
    if (!window.confirm(`Remove "${site.name}" from your list?`)) return
    setDeleteId(site.id)
    try {
      await newsDeleteSite(userId, site.id)
      if (selected?.id === site.id) setSelected(null)
      await loadSites()
    } catch (e) {
      console.error(e)
    } finally {
      setDeleteId(null)
    }
  }

  const grouped = groupByState(sites)

  return (
    <div className="np-page">
      {/* Nav */}
      <nav className="rm-nav">
        <div className="rm-nav-logo">
          <span className="rm-nav-icon">🏛️</span>
          <span className="rm-nav-brand">Civic Lens</span>
        </div>
        <div className="rm-nav-links">
          <span className="rm-nav-link" onClick={onBack}>Dashboard</span>
          <span className="rm-nav-link active">News</span>
        </div>
        <div className="rm-nav-right">
          <div className="rm-avatar">{userId[0]?.toUpperCase()}</div>
        </div>
      </nav>

      <div className="np-body">
        {/* Sidebar */}
        <aside className="np-sidebar">
          <div className="np-sidebar-header">
            <span className="np-sidebar-title">My News Sources</span>
            <button className="np-btn np-btn-add-sm" onClick={() => setShowAdd(true)}>+ Add</button>
          </div>

          {loading ? (
            <div className="np-sidebar-loading">
              <div className="np-spinner-sm" />
            </div>
          ) : sites.length === 0 ? (
            <div className="np-sidebar-empty">
              <div>No sources yet.</div>
              <button className="np-btn np-btn-primary np-btn-full"
                onClick={() => setShowAdd(true)}>+ Add a news source</button>
            </div>
          ) : (
            <div className="np-state-groups">
              {Object.entries(grouped).map(([state, stateSites]) => (
                <div key={state} className="np-state-group">
                  <div className="np-state-label">{state}</div>
                  {stateSites.map(s => (
                    <div key={s.id}
                      className={`np-site-row${selected?.id === s.id ? ' np-site-active' : ''}`}
                      onClick={() => setSelected(s)}>
                      <div className="np-site-info">
                        <span className="np-site-name">{s.name}</span>
                        {s.is_default && <span className="np-default-dot" title="Default source" />}
                      </div>
                      <button className="np-site-del"
                        onClick={e => { e.stopPropagation(); handleDelete(s) }}
                        disabled={deleteId === s.id}
                        title="Remove">
                        {deleteId === s.id ? '…' : '×'}
                      </button>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </aside>

        {/* Main content */}
        <main className="np-main">
          {!selected ? (
            <div className="np-main-empty">
              <div className="np-empty-icon">📰</div>
              <div className="np-empty-title">Select a news source</div>
              <div className="np-empty-sub">
                Pick a site from the sidebar to view its latest articles.<br />
                Articles are fetched fresh once per day and translated to English.
              </div>
              {sites.length === 0 && (
                <button className="np-btn np-btn-primary" onClick={() => setShowAdd(true)}>
                  + Add your first source
                </button>
              )}
            </div>
          ) : (
            <ArticleView key={selected.id} site={selected} userId={userId} />
          )}
        </main>
      </div>

      {showAdd && (
        <AddSiteModal
          availableDefaults={availableDefaults}
          onAdd={handleAdd}
          onClose={() => setShowAdd(false)}
        />
      )}
    </div>
  )
}
