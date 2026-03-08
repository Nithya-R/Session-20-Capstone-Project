import './OptionBar.css'

// Quiz option letters for detection
const QUIZ_LETTERS = ['A)', 'B)', 'C)', 'D)', 'E)']

export default function OptionBar({ options, question, onSelect, disabled }) {
  const isQuiz = question !== null && options.some(o => QUIZ_LETTERS.some(l => o.startsWith(l)))

  if (isQuiz) {
    return (
      <div className="option-quiz">
        {options.map((opt, i) => {
          const letter = String.fromCharCode(65 + i)
          // Strip the "A) " prefix so we show clean text
          const label = opt.replace(/^[A-E]\)\s*/, '')
          return (
            <button
              key={i}
              className="quiz-btn"
              onClick={() => onSelect(letter.toLowerCase())}
              disabled={disabled}
            >
              <span className="quiz-letter">{letter}</span>
              <span className="quiz-label">{label}</span>
            </button>
          )
        })}
      </div>
    )
  }

  return (
    <div className="option-chips">
      {options.map((opt, i) => (
        <button
          key={i}
          className="chip"
          onClick={() => onSelect(opt)}
          disabled={disabled}
        >
          {opt}
        </button>
      ))}
    </div>
  )
}
