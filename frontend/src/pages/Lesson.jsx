import { useEffect, useState } from 'react'
import { api } from '../api'
import { Button, Card } from '../components/ui'
import LearnStage from '../components/LearnStage'
import MemoryCheckStage from '../components/MemoryCheckStage'
import ConversationStage from '../components/ConversationStage'

export default function Lesson({ lessonId, onExit }) {
  const [lesson, setLesson] = useState(null)
  const [stage, setStage] = useState('learn') // learn -> quiz -> chat -> done

  useEffect(() => {
    api.getLesson(lessonId).then(setLesson)
  }, [lessonId])

  if (!lesson) {
    return <div className="min-h-screen flex items-center justify-center text-base-600">Loading lesson…</div>
  }

  if (stage === 'done') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="p-8 text-center max-w-sm animate-pop-in">
          <div className="text-5xl mb-4">🎉</div>
          <div className="text-xl font-bold text-white mb-2">Lesson complete!</div>
          <div className="text-base-600 text-sm mb-6">
            You practiced "{lesson.scenario.title}" — nice work.
          </div>
          <Button onClick={onExit} className="w-full">Back to lessons</Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-md mx-auto px-4 pt-4 flex justify-between items-center">
        <button onClick={onExit} className="text-base-600 text-sm hover:text-white transition-colors">
          ← Exit
        </button>
        <div className="text-base-600 text-xs uppercase tracking-wide">
          {stage === 'learn' && 'Stage 1 · Learn'}
          {stage === 'quiz' && 'Stage 2 · Memory check'}
          {stage === 'chat' && 'Stage 3 · Conversation'}
        </div>
      </div>

      {stage === 'learn' && (
        <LearnStage words={lesson.words} onComplete={() => setStage('quiz')} />
      )}
      {stage === 'quiz' && (
        <MemoryCheckStage
          lessonId={lessonId}
          words={lesson.words}
          onComplete={() => setStage('chat')}
        />
      )}
      {stage === 'chat' && (
        <ConversationStage
          lessonId={lessonId}
          scenarioTitle={lesson.scenario.title}
          onComplete={() => setStage('done')}
        />
      )}
    </div>
  )
}
