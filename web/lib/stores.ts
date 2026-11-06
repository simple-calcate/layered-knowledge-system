import { create } from 'zustand'
import type { Corpus, QuestionNode } from '../types'

interface KnowledgeState {
  corpus: Corpus | null
  questionsById: Record<string, QuestionNode>
  coordinateIndex: Record<string, string>
  load: (c: Corpus) => void
  getQuestion: (id: string) => QuestionNode | undefined
  getByCoordinate: (x: number, y: number) => QuestionNode | undefined
}

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  corpus: null,
  questionsById: {},
  coordinateIndex: {},

  load: (c) => {
    const questionsById: Record<string, QuestionNode> = {}
    const coordinateIndex: Record<string, string> = {}
    for (const q of c.questions) {
      questionsById[q.id] = q
      coordinateIndex[`${q.x}_${q.y}`] = q.id
    }
    set({ corpus: c, questionsById, coordinateIndex })
  },

  getQuestion: (id) => get().questionsById[id],
  getByCoordinate: (x, y) => {
    const id = get().coordinateIndex[`${x}_${y}`]
    return id ? get().questionsById[id] : undefined
  },
}))

interface CanvasState {
  selectedQuestionId: string | null
  showBlanks: boolean
  selectQuestion: (id: string | null) => void
  toggleBlanks: () => void
}

export const useCanvasStore = create<CanvasState>((set) => ({
  selectedQuestionId: null,
  showBlanks: true,
  selectQuestion: (id) => set({ selectedQuestionId: id }),
  toggleBlanks: () => set((s) => ({ showBlanks: !s.showBlanks })),
}))

/** v3：每题只有一个正确答案，抽屉只需记住「当前看哪一条改写」。 */
interface AnswerState {
  isOpen: boolean
  answerMap: Record<string, string>
  openDrawer: () => void
  closeDrawer: () => void
  chooseAnswer: (questionId: string, answerId: string) => void
}

export const useAnswerStore = create<AnswerState>((set) => ({
  isOpen: false,
  answerMap: {},
  openDrawer: () => set({ isOpen: true }),
  closeDrawer: () => set({ isOpen: false }),
  chooseAnswer: (questionId, answerId) =>
    set((s) => ({ answerMap: { ...s.answerMap, [questionId]: answerId } })),
}))
