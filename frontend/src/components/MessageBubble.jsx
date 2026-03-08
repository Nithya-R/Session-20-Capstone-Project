import './MessageBubble.css'

function renderLine(line, i) {
  const t = line.trim()

  if (!t) return null

  // Divider
  if (/^-{3,}$/.test(t) || /^={3,}$/.test(t))
    return <hr key={i} className="bubble-divider" />

  // Section heading (## ...)
  if (/^#{1,3}\s/.test(line)) {
    const text = line.replace(/^#+\s*/, '')
    return <p key={i} className="bubble-heading">{text}</p>
  }

  // "Part N of M" label
  if (/^Part \d+ of \d+$/.test(t))
    return <p key={i} className="bubble-part-label">{t}</p>

  // "Hint:" line at bottom of snippets
  if (t.startsWith('Type any question'))
    return <p key={i} className="bubble-hint">{t}</p>

  // Q&A prefix
  if (t.startsWith('Q: '))
    return <p key={i} className="bubble-q">{t}</p>

  // Quiz question header Q1/7:
  if (/^Q\d+\/\d+:/.test(t))
    return <p key={i} className="bubble-question-head">{t}</p>

  // Answer options inside bubble
  if (/^\s{2}[A-E]\)/.test(line))
    return <p key={i} className="bubble-option">{t}</p>

  // Bullet (* text or • text)
  if (/^\*\s+/.test(t) || /^•\s+/.test(t) || /^-\s+/.test(t)) {
    const text = t.replace(/^[*•-]\s+/, '')
    // Handle **bold** inside bullet
    return <p key={i} className="bubble-bullet">{parseBold(text)}</p>
  }

  return <p key={i}>{parseBold(t)}</p>
}

function parseBold(text) {
  if (!text.includes('**')) return text
  const parts = text.split(/\*\*/)
  return parts.map((p, j) => j % 2 === 1 ? <strong key={j}>{p}</strong> : p)
}

export default function MessageBubble({ role, text, isLesson }) {
  const isAgent = role === 'agent'
  const lines = text.split('\n')

  return (
    <div className={`bubble-wrap ${isAgent ? 'agent' : 'user'}`}>
      {isAgent && <div className="bubble-avatar">🏛️</div>}
      <div className={`bubble ${isAgent ? 'bubble-agent' : 'bubble-user'} ${isLesson ? 'bubble-lesson' : ''}`}>
        {lines.map((line, i) => renderLine(line, i)).filter(Boolean)}
      </div>
    </div>
  )
}
