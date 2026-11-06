import { useEffect } from 'react'
import corpusJson from './data/corpus.json'
import type { Corpus } from './types'
import { useKnowledgeStore, useCanvasStore, useAnswerStore } from './lib/stores'
import { KnowledgeCanvas } from './components/KnowledgeCanvas'
import { AnswerDrawer } from './components/AnswerDrawer'
import { columnColor } from './theme'

const corpus = corpusJson as unknown as Corpus

export default function App() {
  const load = useKnowledgeStore((s) => s.load)
  const selectedQuestionId = useCanvasStore((s) => s.selectedQuestionId)
  const selectQuestion = useCanvasStore((s) => s.selectQuestion)
  const showBlanks = useCanvasStore((s) => s.showBlanks)
  const toggleBlanks = useCanvasStore((s) => s.toggleBlanks)
  const openDrawer = useAnswerStore((s) => s.openDrawer)
  const closeDrawer = useAnswerStore((s) => s.closeDrawer)
  const isOpen = useAnswerStore((s) => s.isOpen)

  useEffect(() => {
    load(corpus)
  }, [load])

  useEffect(() => {
    if (selectedQuestionId) openDrawer()
    else closeDrawer()
  }, [selectedQuestionId, openDrawer, closeDrawer])

  const s = corpus.stats
  const cols = corpus.app.axes.x_list

  return (
    <div className="app">
      <header className="topbar">
        <div className="title-block">
          <h1>{corpus.app.title}</h1>
          <span className="subtitle">{corpus.app.subtitle}</span>
        </div>
        <div className="stats">
          <span>问题 <b>{s.questions}</b></span>
          <span>正确答案 <b>{s.canonicals}</b></span>
          <span>说法 <b>{s.answers}</b></span>
          <span className="muted">空缺 {s.cells_open} 格</span>
        </div>
        <div className="controls">
          <label className="switch">
            <input type="checkbox" checked={showBlanks} onChange={toggleBlanks} />
            显示空缺格
          </label>
          {selectedQuestionId && (
            <button className="ghost-btn" onClick={() => selectQuestion(null)}>取消选中</button>
          )}
        </div>
      </header>

      <div className="main">
        <div className="legend">
          {cols.map((c) => (
            <span key={c.x} className="legend-item">
              <i className="dot" style={{ background: columnColor(c.x) }} />
              X{c.x} {c.label}
            </span>
          ))}
          <span className="legend-hint">点任意问题格查看正确答案与它的不同说法</span>
        </div>
        <KnowledgeCanvas corpus={corpus} />
        {isOpen && selectedQuestionId && <AnswerDrawer questionId={selectedQuestionId} />}
      </div>

      <footer className="footer">
        数据源 {corpus.app.source_path} · 一个文件一张卡片，欢迎添砖加瓦 · 生成于 {corpus.app.generated_at}
      </footer>
    </div>
  )
}
