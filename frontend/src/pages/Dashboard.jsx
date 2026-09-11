import { useEffect, useState } from 'react'
import { api, setToken } from '../api'
import { Card, StreakBadge } from '../components/ui'

export default function Dashboard({ user, onOpenLesson, onLogout }) {
  const [lessons, setLessons] = useState([])
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.listLessons(), api.getProgress()])
      .then(([l, p]) => {
        setLessons(l)
        setProgress(p)
      })
      .finally(() => setLoading(false))
  }, [])

  function logout() {
    setToken(null)
    onLogout()
  }

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-lg mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="text-xl font-bold text-white">
              {user?.display_name ? `Hi, ${user.display_name}` : 'Welcome back'}
            </div>
            <div className="text-base-600 text-sm">Ready for today's lesson?</div>
          </div>
          <button onClick={logout} className="text-base-600 text-sm hover:text-white transition-colors">
            Log out
          </button>
        </div>

        {progress && (
          <div className="grid grid-cols-3 gap-3 mb-8">
            <Card className="p-4 text-center">
              <StreakBadge streak={progress.current_streak} />
              <div className="text-base-600 text-xs mt-2">day streak</div>
            </Card>
            <Card className="p-4 text-center">
              <div className="text-lg font-bold text-accent">{progress.xp}</div>
              <div className="text-base-600 text-xs mt-1">XP</div>
            </Card>
            <Card className="p-4 text-center">
              <div className="text-lg font-bold text-white">{progress.words_mastered}</div>
              <div className="text-base-600 text-xs mt-1">words mastered</div>
            </Card>
          </div>
        )}

        <div className="text-sm font-semibold text-base-600 uppercase tracking-wide mb-3">
          Lessons
        </div>

        {loading && <div className="text-base-600 text-sm">Loading…</div>}

        <div className="space-y-3">
          {lessons.map((lesson) => (
            <Card
              key={lesson.id}
              className="p-4 flex items-center justify-between cursor-pointer hover:border-accent transition-colors group"
              onClick={() => onOpenLesson(lesson.id)}
            >
              <div>
                <div className="font-semibold text-white group-hover:text-accent transition-colors">
                  {lesson.title}
                </div>
                <div className="text-base-600 text-sm">{lesson.scenario_title}</div>
              </div>
              <div className="text-base-600 text-sm">{lesson.word_count} words →</div>
            </Card>
          ))}
          {!loading && lessons.length === 0 && (
            <div className="text-base-600 text-sm">No lessons yet for your learning language.</div>
          )}
        </div>
      </div>
    </div>
  )
}
