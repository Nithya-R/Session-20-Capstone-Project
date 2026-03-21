const BASE = '/api/v1'

export async function startSession(userId, resume = true, targetLevel = null, targetMode = null) {
  const res = await fetch(`${BASE}/conversation/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      resume,
      target_level: targetLevel,
      target_mode: targetMode,
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function respond(sessionId, input) {
  const res = await fetch(`${BASE}/conversation/${sessionId}/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getStatus(userId) {
  const res = await fetch(`${BASE}/training/status?user_id=${encodeURIComponent(userId)}`)
  if (!res.ok) return null
  return res.json()
}

export async function getRoadmap(userId) {
  const res = await fetch(`${BASE}/training/roadmap?user_id=${encodeURIComponent(userId)}`)
  if (!res.ok) return null
  return res.json()
}

export async function askQuestion(userId, question) {
  const res = await fetch(`${BASE}/qa/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, question }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getQAHistory(userId) {
  const res = await fetch(`${BASE}/qa/history?user_id=${encodeURIComponent(userId)}`)
  if (!res.ok) return { history: [] }
  return res.json()
}

// ── Admin API ──────────────────────────────────────────────────────────────

export async function adminListFiles() {
  const res = await fetch(`${BASE}/admin/data/files`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function adminUploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/admin/data/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function adminDeleteFile(filename) {
  const res = await fetch(`${BASE}/admin/data/files/${encodeURIComponent(filename)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function adminFileContentUrl(filename) {
  return `${BASE}/admin/data/files/${encodeURIComponent(filename)}/content`
}

export async function adminGetTextContent(filename) {
  const res = await fetch(adminFileContentUrl(filename))
  if (!res.ok) throw new Error(await res.text())
  return res.text()
}

export async function adminListLessons() {
  const res = await fetch(`${BASE}/admin/lessons`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function adminGetLesson(level) {
  const res = await fetch(`${BASE}/admin/lessons/${level}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function adminGetQuiz(level) {
  const res = await fetch(`${BASE}/admin/lessons/${level}/quiz`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function adminUpdateLesson(level, content, regenerateQuiz = false) {
  const res = await fetch(`${BASE}/admin/lessons/${level}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ level, content, regenerate_quiz: regenerateQuiz }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function adminGenerateLesson(level, prompt, regenerateQuiz = false) {
  const res = await fetch(`${BASE}/admin/lessons/${level}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, regenerate_quiz: regenerateQuiz }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function adminRegenerateQuiz(level, lessonContent) {
  const res = await fetch(`${BASE}/admin/lessons/${level}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ level, content: lessonContent, regenerate_quiz: true }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ── News API ────────────────────────────────────────────────────────────────

export async function newsGetSites(userId) {
  const res = await fetch(`${BASE}/news/sites/${encodeURIComponent(userId)}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function newsAddSite(userId, state, name, url, siteId = null) {
  const res = await fetch(`${BASE}/news/sites/${encodeURIComponent(userId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state, name, url, site_id: siteId }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function newsDeleteSite(userId, siteId) {
  const res = await fetch(
    `${BASE}/news/sites/${encodeURIComponent(userId)}/${encodeURIComponent(siteId)}`,
    { method: 'DELETE' }
  )
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function newsGetArticles(siteId, url, name) {
  const params = new URLSearchParams({ url, name })
  const res = await fetch(`${BASE}/news/articles/${encodeURIComponent(siteId)}?${params}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ── Simulator API ────────────────────────────────────────────────────────────

export async function evaluateBill(title, description, goals) {
  const res = await fetch(`${BASE}/simulator/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description, goals }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
