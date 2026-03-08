import './QuizReview.css'

export default function QuizReview({ review, onDone, doneLabel = 'Continue' }) {
  return (
    <div className="quiz-review">
      <div className="qr-header">
        <span className="qr-score">
          {review.filter(r => r.correct).length}/{review.length} Correct
        </span>
        <button className="btn-qr-done" onClick={onDone}>{doneLabel} →</button>
      </div>

      <div className="qr-list">
        {review.map((r, i) => (
          <div key={i} className={`qr-item ${r.correct ? 'correct' : 'wrong'}`}>
            <div className="qr-item-header">
              <span className="qr-badge">{r.correct ? '✓' : '✗'}</span>
              {r.level && <span className="qr-level">Level {r.level}</span>}
              <span className="qr-question">{r.question}</span>
            </div>

            <div className="qr-options">
              {r.options.map((opt, idx) => {
                const isUser    = idx === r.user_choice
                const isCorrect = idx === r.correct_index
                let cls = 'qr-opt'
                if (isCorrect) cls += ' qr-opt-correct'
                else if (isUser && !isCorrect) cls += ' qr-opt-wrong'
                return (
                  <div key={idx} className={cls}>
                    <span className="qr-opt-letter">{String.fromCharCode(65 + idx)}</span>
                    <span className="qr-opt-text">{opt}</span>
                    {isCorrect && <span className="qr-marker correct-marker">✓ Correct</span>}
                    {isUser && !isCorrect && <span className="qr-marker wrong-marker">✗ Your answer</span>}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
