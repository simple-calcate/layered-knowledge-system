export interface Coordinate {
  x: number
  y: number
  breadth_label: string
  depth_label: string
}

export interface KnowledgeNode {
  id: string
  title: string
  term: string
  focus: string
  strict_definition: string
  core_mechanics: string
  key_formulas: string[]
  boundary: string
  intuition: string
  tags: string[]
  status: string
  version: number
  family_key: string
  family_label: string
  stratum: number
  stratum_label: string
  x: number
  y: number
  breadth_label: string
  depth_label: string
  plane_coordinate: Coordinate
  prerequisites: string[]
  extends: string[]
  related: string[]
  prerequisite_refs: string[]
  exercise_ids: string[]
}

export interface AnswerVariant {
  variant_id: string
  style: string
  register: string
  content: string
  covers_steps: string[]
  misses_steps: string[]
}

export interface Exercise {
  id: string
  node_ids: string[]
  primary_node_id: string
  ex_type: string
  title: string
  difficulty: number | null
  stem: string
  hints: string[]
  semantic_invariants: string[]
  invariant_ids: string[]
  checks: { kind: string; name: string; code: string }[]
  answers: AnswerVariant[]
}

/** 广度轴刻度：概念族，x 为列号（1..N） */
export interface AxisFamily {
  key: string
  x: number
  label: string
  desc: string
}

/** 深度轴刻度：机制层，value 为层号（1..M） */
export interface AxisStratum {
  key: string
  value: number
  label: string
  desc: string
}

export interface Axes {
  x_label: string
  y_label: string
  x_list: AxisFamily[]
  x_families: AxisFamily[]
  y_list: AxisStratum[]
}

export interface AppMeta {
  topic_id: string
  title: string
  subtitle: string
  version: number
  updated_at: string
  source_path: string
  generated_at: string
  description: string
  axes: Axes
  conventions: Record<string, unknown>
  authoring_rules: string[]
}

export interface Corpus {
  app: AppMeta
  nodes: KnowledgeNode[]
  exercises: Exercise[]
  cheatsheet: { node_id: string; title: string; term: string; focus: string }[]
  stats: Record<string, number>
}
