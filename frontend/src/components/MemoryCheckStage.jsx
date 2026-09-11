import { useState } from 'react'
import { api } from '../api'
import { Card, Button, ProgressBar } from '../components/ui'

export default function MemoryCheckStage({ lessonId, words, onComplete }) {
  const [index, setIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const word = words[index]

  async function submit(e) {
    e.preventDefault()
    if (!answer.trim() || submitting) return
    setSubmitting(true)
    try {
      const res = await api.memoryCheck(lessonId, word.id, answer)
      setResult(res)
    } finally {
      setSubmitting(false)
    }
  }

  function next() {
    setAnswer('')
    setResult(null)
    if (index + 1 >= words.length) onComplete()
    else setIndex(index + 1)
  }

  const feedbackColor = result?.correct ? 'text-accent' : result?.almost ? 'text-yellow-400' : 'text-red-400'
  const feedbackIcon = result?.correct ? '✅' : result?.almost ? '〜' : '✕'

  return (
    <div className="max-w-md mx-auto px-4 pt-10">
      <ProgressBar value={index} max={words.length} />
      <div className="text-base-600 text-xs mt-2 mb-8">
        Question {index + 1} of {words.length}
      </div>

      <Card className="p-8 text-center">
        <div className="text-base-600 text-sm mb-2">How do you say...</div>
        <div className="text-2xl font-extrabold text-white mb-6">{word.translation}</div>

        {!result ? (
          <form onSubmit={submit}>
            <input
              autoFocus
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your answer"
              className="w-full bg-base-800 border border-base-700 rounded-xl px-4 py-2.5 text-white text-center placeholder-base-600 outline-none focus:border-accent transition-colors"
            />
            <Button type="submit" disabled={submitting} className="w-full mt-4">
              Check
            </Button>
          </form>
        ) : (
          <div className="animate-pop-in">
            <div className={`text-2xl mb-2 ${feedbackColor}`}>{feedbackIcon}</div>
            <div className={`text-sm ${feedbackColor} mb-6`}>{result.message}</div>
            <Button onClick={next} className="w-full">
              {index + 1 >= words.length ? 'Continue to conversation' : 'Next'}
            </Button>
          </div>
        )}
      </Card>
    </div>
  )
}
