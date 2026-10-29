import { create } from 'zustand'
import type { Corpus, Exercise, KnowledgeNode } from '../types'

interface KnowledgeState {
  corpus: Corpus | null
  nodesById: Record<string, KnowledgeNode>
  exercisesById: Record<string, Exercise>
  exercisesByNode: Record<string, Exercise[]>
  coordinateIndex: Record<string, string>
  load: (c: Corpus) => void
  getExercises: (nodeId: string) => Exercise[]
  getNodeByCoordinate: (x: number, y: number) => KnowledgeNode | undefined
}

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  corpus: null,
  nodesById: {},
  exercisesById: {},
  exercisesByNode: {},
  coordinateIndex: {},

  load: (c) => {
    const nodesById: Record<string, KnowledgeNode> = {}
    const coordinateIndex: Record<string, string> = {}
    for (const n of c.nodes) {
      nodesById[n.id] = n
      coordinateIndex[`${n.x}_${n.y}`] = n.id
    }
    const exercisesById: Record<string, Exercise> = {}
    const exercisesByNode: Record<string, Exercise[]> = {}
    for (const e of c.exercises) {
      exercisesById[e.id] = e
      const key = e.primary_node_id
      exercisesByNode[key] = exercisesByNode[key] ? [...exercisesByNode[key], e] : [e]
    }
    set({ corpus: c, nodesById, exercisesById, exercisesByNode, coordinateIndex })
  },

  getExercises: (nodeId) => get().exercisesByNode[nodeId] ?? [],
  getNodeByCoordinate: (x, y) => {
    const id = get().coordinateIndex[`${x}_${y}`]
    return id ? get().nodesById[id] : undefined
  },
}))

interface CanvasState {
  selectedNodeId: string | null
  hoveredNodeId: string | null
  showBlanks: boolean
  showEdges: boolean
  selectNode: (id: string | null) => void
  setHovered: (id: string | null) => void
  toggleBlanks: () => void
  toggleEdges: () => void
}

export const useCanvasStore = create<CanvasState>((set) => ({
  selectedNodeId: null,
  hoveredNodeId: null,
  showBlanks: true,
  showEdges: true,
  selectNode: (id) => set({ selectedNodeId: id }),
  setHovered: (id) => set({ hoveredNodeId: id }),
  toggleBlanks: () => set((s) => ({ showBlanks: !s.showBlanks })),
  toggleEdges: () => set((s) => ({ showEdges: !s.showEdges })),
}))

interface DrawerState {
  isOpen: boolean
  activeExerciseIndex: number
  selectedVariantMap: Record<string, string>
  comparisonMode: boolean
  openDrawer: () => void
  closeDrawer: () => void
  setActiveExerciseIndex: (i: number) => void
  selectVariant: (exerciseId: string, variantId: string) => void
  toggleComparison: () => void
}

export const useExerciseStore = create<DrawerState>((set) => ({
  isOpen: false,
  activeExerciseIndex: 0,
  selectedVariantMap: {},
  comparisonMode: false,
  openDrawer: () => set({ isOpen: true, activeExerciseIndex: 0 }),
  closeDrawer: () => set({ isOpen: false }),
  setActiveExerciseIndex: (i) => set({ activeExerciseIndex: i }),
  selectVariant: (exerciseId, variantId) =>
    set((s) => ({ selectedVariantMap: { ...s.selectedVariantMap, [exerciseId]: variantId } })),
  toggleComparison: () => set((s) => ({ comparisonMode: !s.comparisonMode })),
}))
