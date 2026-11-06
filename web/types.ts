export interface AxisLevelX {
  x: number
  key: string
  label: string
  desc: string
}

export interface AxisLevelY {
  y: number
  key: string
  label: string
  desc: string
}

export interface Attribution {
  name: string
  link?: string
}

export interface SourceNote {
  type: string
  note: string
}

export interface Invariant {
  id: string
  claim: string
}

export interface ReviewInfo {
  status: string
  by: string
  at: string
  policy?: string
}

/** 一道题唯一被认定为正确的答案：要点清单 + 认定依据 + 审核信息。 */
export interface Canonical {
  id: string
  invariants: Invariant[]
  basis: string
  author: Attribution
  review: ReviewInfo
}

export interface AnswerCard {
  id: string
  style: string
  register: string
  content: string
  content_hash: string
  covers: string[]
  misses: string[]
  author: Attribution
  source: SourceNote
  created_at: string
}

export interface QuestionNode {
  id: string
  concept_id: string
  x: number
  y: number
  breadth_label: string
  depth_label: string
  text: string
  note: string
  author: Attribution
  created_at: string
  canonical: Canonical | null
  answers: AnswerCard[]
  has_canonical: boolean
  answer_count: number
}

export interface ConceptMeta {
  id: string
  term: string
  aliases: string[]
  summary: string
  author: Attribution
  created_at: string
  status: string
  question_count?: number
}

export interface AppMeta {
  title: string
  subtitle: string
  version: number
  generated_at: string
  source_path: string
  axes: {
    x_label: string
    y_label: string
    x_list: AxisLevelX[]
    y_list: AxisLevelY[]
  }
  gap_policy: string
}

export interface Corpus {
  app: AppMeta
  concept: ConceptMeta
  concepts: ConceptMeta[]
  questions: QuestionNode[]
  stats: Record<string, number>
}
