import { useEffect, useMemo } from 'react'
import corpusJson from './data/corpus.json'
import type { Corpus } from './types'
import { useKnowledgeStore, useCanvasStore, useExerciseStore } from './lib/stores'
import { KnowledgeCanvas } from './components/KnowledgeCanvas'
import { ExerciseDrawer } from './components/ExerciseDrawer'
import { familyColor } from './theme'

const corpus = corpusJson as unknown as Corpus

export default function App() {
  const load = useKnowledgeStore((s) => s.load)
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId)
  const selectNode = useCanvasStore((s) => s.selectNode)
  const showBlanks = useCanvasStore((s) => s.showBlanks)
  const showEdges = useCanvasStore((s) => s.showEdges)
  const toggleBlanks = useCanvasStore((s) => s.toggleBlanks)
  const toggleEdges = useCanvasStore((s) => s.toggleEdges)
  const openDrawer = useExerciseStore((s) => s.openDrawer)
  const isOpen = useExerciseStore((s) => s.isOpen)
  const closeDrawer = useExerciseStore((s) => s.closeDrawer)

  useEffect(() => {
    load(corpus)
  }, [load])

  useEffect(() => {
    if (selectedNodeId) {
      openDrawer()
    } else {
      closeDrawer()
    }
  }, [selectedNodeId, openDrawer, closeDrawer])

  const stats = corpus.stats
  const legend = useMemo(() => corpus.app.axes.x_families, [])

  return (
    <div className="app">
      <header className="topbar">
        <div className="title-block">
          <h1>{corpus.app.title}</h1>
          <span className="subtitle">{corpus.app.subtitle}</span>
        </div>

        <div className="stats">
          <span>
            节点 <b>{stats.nodes}</b>
          </span>
          <span>
            习题 <b>{stats.exercises}</b>
          </span>
          <span>
            解答变体 <b>{stats.answer_variants}</b>
          </span>
          <span className="muted">v{corpus.app.version}</span>
        </div>

        <div className="controls">
          <label className="switch">
            <input type="checkbox" checked={showBlanks} onChange={toggleBlanks} />
            显示空缺格
          </label>
          <label className="switch">
            <input type="checkbox" checked={showEdges} onChange={toggleEdges} />
            显示依赖边
          </label>
          {selectedNodeId && (
            <button className="ghost-btn" onClick={() => selectNode(null)}>
              取消选中
            </button>
          )}
        </div>
      </header>

      <div className="main">
        <div className="legend">
          {legend.map((f) => (
            <span key={f.key} className="legend-item">
              <i className="dot" style={{ background: familyColor(f.key) }} />
              {f.label}
            </span>
          ))}
        </div>
        <KnowledgeCanvas corpus={corpus} />
        {isOpen && selectedNodeId && <ExerciseDrawer nodeId={selectedNodeId} />}
      </div>

      <footer className="footer">
        数据源 {corpus.app.source_path} · 生成于 {corpus.app.generated_at}
      </footer>
    </div>
  )
}
