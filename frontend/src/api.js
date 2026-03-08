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
