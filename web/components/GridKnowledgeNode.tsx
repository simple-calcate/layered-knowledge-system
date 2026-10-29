import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import { familyColor, STRATUM_TINT } from '../theme'
import type { KnowledgeNode as KNode } from '../types'

export const GridKnowledgeNode = memo(function GridKnowledgeNode({
  data,
  selected,
}: {
  data: { node: KNode }
  selected: boolean
}) {
  const n = data.node
  const color = familyColor(n.family_key)

  return (
    <div
      className={`card ${selected ? 'sel' : ''}`}
      style={{
        borderLeft: `4px solid ${color}`,
        background: STRATUM_TINT[n.stratum] ?? '#fff',
        width: 232,
        height: 118,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="card-top">
        <span className="coord" style={{ color }}>
          X{n.x} Y{n.y}
        </span>
        <span className="ex-badge">{n.exercise_ids.length} 题</span>
      </div>
      <div className="card-title">{n.title}</div>
      <div className="card-def">{n.strict_definition}</div>
      <div className="card-foot">{n.stratum_label}</div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  )
})
