import { useMemo } from 'react'
import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
} from '@xyflow/react'
import type { Node, NodeTypes } from '@xyflow/react'
import type { Corpus } from '../types'
import { QuestionCard } from './QuestionCard'
import { AxisChip, BlankCell } from './AxisChip'
import { useCanvasStore } from '../lib/stores'

const CELL_W = 270
const CELL_H = 152
const GAP_X = 40
const GAP_Y = 44
const OFFSET_X = 200
const OFFSET_Y = 90

const nodeTypes: NodeTypes = {
  question: QuestionCard,
  axis: AxisChip,
  blank: BlankCell,
} as unknown as NodeTypes

export function KnowledgeCanvas({ corpus }: { corpus: Corpus }) {
  const selectedQuestionId = useCanvasStore((s) => s.selectedQuestionId)
  const showBlanks = useCanvasStore((s) => s.showBlanks)
  const selectQuestion = useCanvasStore((s) => s.selectQuestion)

  const nodes = useMemo(() => {
    const colX = (x: number) => OFFSET_X + (x - 1) * (CELL_W + GAP_X)
    const rowY = (y: number) => OFFSET_Y + (y - 1) * (CELL_H + GAP_Y)
    const list: Node[] = []
    const cols = corpus.app.axes.x_list
    const rows = corpus.app.axes.y_list

    for (const c of cols) {
      list.push({
        id: `axis-col-${c.x}`,
        type: 'axis',
        position: { x: colX(c.x), y: 0 },
        draggable: false,
        selectable: false,
        data: { kind: 'col', text: `X${c.x} ${c.label}`, sub: c.desc },
        style: { width: CELL_W },
      })
    }
    for (const r of rows) {
      list.push({
        id: `axis-row-${r.y}`,
        type: 'axis',
        position: { x: 0, y: rowY(r.y) + 36 },
        draggable: false,
        selectable: false,
        data: { kind: 'row', text: `Y${r.y} ${r.label}`, sub: r.desc },
        style: { width: 176 },
      })
    }

    const byCell = new Map(corpus.questions.map((q) => [`${q.x}_${q.y}`, q]))
    if (showBlanks) {
      for (const c of cols) {
        for (const r of rows) {
          if (byCell.has(`${c.x}_${r.y}`)) continue
          list.push({
            id: `blank-${c.x}-${r.y}`,
            type: 'blank',
            position: { x: colX(c.x), y: rowY(r.y) },
            draggable: false,
            selectable: false,
            data: { text: '空缺 · 等人来问' },
            style: { width: CELL_W, height: CELL_H },
          })
        }
      }
    }

    for (const q of corpus.questions) {
      list.push({
        id: q.id,
        type: 'question',
        position: { x: colX(q.x), y: rowY(q.y) },
        draggable: false,
        selectable: false,
        data: { node: q },
        selected: selectedQuestionId === q.id,
        style: { width: CELL_W, height: CELL_H },
      })
    }
    return list
  }, [corpus, selectedQuestionId, showBlanks])

  return (
    <div className="canvas-area">
      <ReactFlow
        nodes={nodes}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => {
          if (node.type === 'question') selectQuestion(node.id)
        }}
        nodesConnectable={false}
        elementsSelectable={false}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        minZoom={0.15}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#d8dee9" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
