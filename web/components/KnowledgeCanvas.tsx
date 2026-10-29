import { useMemo } from 'react'
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
} from '@xyflow/react'
import type { Edge, Node } from '@xyflow/react'
import type { Corpus } from '../types'
import { GridKnowledgeNode } from './GridKnowledgeNode'
import { AxisChip, BlankCell } from './AxisChip'
import { useCanvasStore } from '../lib/stores'

const CELL_W = 260
const CELL_H = 150
const GAP_X = 40
const GAP_Y = 44
const OFFSET_X = 200
const OFFSET_Y = 90

const nodeTypes = {
  know: GridKnowledgeNode,
  axis: AxisChip,
  blank: BlankCell,
}

export function KnowledgeCanvas({ corpus }: { corpus: Corpus }) {
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId)
  const showBlanks = useCanvasStore((s) => s.showBlanks)
  const showEdges = useCanvasStore((s) => s.showEdges)
  const selectNode = useCanvasStore((s) => s.selectNode)

  const { nodes, edges } = useMemo(() => {
    const colX = (x: number) => OFFSET_X + (x - 1) * (CELL_W + GAP_X)
    const rowY = (y: number) => OFFSET_Y + (y - 1) * (CELL_H + GAP_Y)

    const list: Node[] = []
    const families = corpus.app.axes.x_families
    const strata = corpus.app.axes.y_list

    for (const fam of families) {
      list.push({
        id: `axis-col-${fam.key}`,
        type: 'axis',
        position: { x: colX(fam.x), y: 0 },
        draggable: false,
        selectable: false,
        data: { kind: 'col', text: `X${fam.x} ${fam.label}`, sub: fam.desc },
        style: { width: CELL_W },
      })
    }

    for (const lv of strata) {
      list.push({
        id: `axis-row-${lv.value}`,
        type: 'axis',
        position: { x: 0, y: rowY(lv.value) + 40 },
        draggable: false,
        selectable: false,
        data: { kind: 'row', text: `Y${lv.value} ${lv.label}`, sub: lv.desc },
        style: { width: 170 },
      })
    }

    const filled = new Set(corpus.nodes.map((n) => `${n.x}_${n.y}`))
    if (showBlanks) {
      for (const fam of families) {
        for (const lv of strata) {
          if (filled.has(`${fam.x}_${lv.value}`)) continue
          list.push({
            id: `blank-${fam.x}-${lv.value}`,
            type: 'blank',
            position: { x: colX(fam.x), y: rowY(lv.value) },
            draggable: false,
            selectable: false,
            data: { text: '空缺 · 不补概念' },
            style: { width: CELL_W, height: CELL_H },
          })
        }
      }
    }

    for (const n of corpus.nodes) {
      list.push({
        id: n.id,
        type: 'know',
        position: { x: colX(n.x), y: rowY(n.y) },
        draggable: false,
        data: { node: n },
        selected: selectedNodeId === n.id,
        style: { width: CELL_W, height: CELL_H },
      })
    }

    const ids = new Set(corpus.nodes.map((n) => n.id))
    const e: Edge[] = []
    if (showEdges) {
      for (const n of corpus.nodes) {
        for (const p of n.prerequisites) {
          if (!ids.has(p)) continue
          e.push({
            id: `${p}->${n.id}`,
            source: p,
            target: n.id,
            animated: false,
            style: { stroke: '#98a2b3', strokeWidth: 1.4 },
          })
        }
      }
    }
    return { nodes: list, edges: e }
  }, [corpus, selectedNodeId, showBlanks, showEdges])

  return (
    <div className="canvas-area">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => {
          if (node.type === 'know') {
            selectNode(node.id)
          }
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
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  )
}
