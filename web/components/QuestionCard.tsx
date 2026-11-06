import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { QuestionNode } from '../types'
import { columnColor, DEPTH_TINT } from '../theme'

function Card({ data, selected }: NodeProps & { data: { node: QuestionNode } }) {
  const q = data.node
  const answered = q.has_canonical
  return (
    <div
      className={`card${selected ? ' sel' : ''}${answered ? '' : ' pending'}`}
      style={{ borderLeftColor: columnColor(q.x), background: DEPTH_TINT[q.y] ?? '#ffffff' }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="card-top">
        <span className="coord-chip">X{q.x} Y{q.y}</span>
        <span className={answered ? 'count-badge' : 'count-badge muted'}>
          {answered ? `${q.answer_count} 种说法` : '待补'}
        </span>
      </div>
      <div className="card-title">{q.text}</div>
      <div className="card-note">{q.note || q.depth_label}</div>
      <div className="card-foot">{q.breadth_label} × {q.depth_label}</div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  )
}

export const QuestionCard = memo(Card)
