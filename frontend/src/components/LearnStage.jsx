import { useState } from 'react'
import { Card, Button, ProgressBar } from '../components/ui'

export default function LearnStage({ words, onComplete }) {
  const [index, setIndex] = useState(0)
  const word = words[index]

  function next() {
    if (index + 1 >= words.length) onComplete()
    else setIndex(index + 1)
  }

  return (
    <div className="max-w-md mx-auto px-4 pt-10">
      <ProgressBar value={index} max={words.length} />
      <div className="text-base-600 text-xs mt-2 mb-8">
        Word {index + 1} of {words.length}
      </div>

      <Card key={word.id} className="p-8 text-center animate-pop-in">
        <div className="text-base-600 text-sm mb-2">{word.translation}</div>
        <div className="text-4xl font-extrabold text-white mb-3">{word.term}</div>
        {word.pronunciation && (
          <div className="text-accent text-sm font-medium mb-6">/{word.pronunciation}/</div>
        )}

        {word.example_sentence && (
          <div className="bg-base-800 rounded-xl p-4 text-left mt-4">
            <div className="text-white text-sm">{word.example_sentence}</div>
            <div className="text-base-600 text-xs mt-1">{word.example_translation}</div>
          </div>
        )}

        {word.literal_meaning && (
          <div className="text-base-600 text-xs mt-3 italic">
            literally: "{word.literal_meaning}"
          </div>
        )}
      </Card>

      <Button onClick={next} className="w-full mt-6">
        {index + 1 >= words.length ? "I've got it — quiz me" : 'Next word'}
      </Button>
    </div>
  )
}
