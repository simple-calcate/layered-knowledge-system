import { useExerciseStore, useKnowledgeStore } from '../lib/stores'
import { Markdown } from './Markdown'
import { familyColor } from '../theme'

export function ExerciseDrawer({ nodeId }: { nodeId: string }) {
  const node = useKnowledgeStore((s) => s.nodesById[nodeId])
  const exercises = useKnowledgeStore((s) => s.exercisesByNode[nodeId] ?? [])
  const closeDrawer = useExerciseStore((s) => s.closeDrawer)
  const activeIndex = useExerciseStore((s) => s.activeExerciseIndex)
  const setActiveIndex = useExerciseStore((s) => s.setActiveExerciseIndex)
  const selectedVariantMap = useExerciseStore((s) => s.selectedVariantMap)
  const selectVariant = useExerciseStore((s) => s.selectVariant)

  if (!node) return null

  const ex = exercises[activeIndex]
  const variantId = ex ? selectedVariantMap[ex.id] ?? ex.answers[0]?.variant_id : undefined
  const variant = ex?.answers.find((a) => a.variant_id === variantId) ?? ex?.answers[0]
  const color = familyColor(node.family_key)

  return (
    <aside className="drawer">
      <div className="drawer-head" style={{ borderTop: `3px solid ${color}` }}>
        <div>
          <div className="drawer-coord">
            X{node.x} · Y{node.y} &nbsp;|&nbsp; {node.family_label} &nbsp;·&nbsp; {node.stratum_label}
          </div>
          <h2>{node.term || node.title}</h2>
          <div className="drawer-sub">{node.focus}</div>
        </div>
        <button className="close-btn" onClick={closeDrawer} aria-label="关闭">
          ✕
        </button>
      </div>

      <div className="drawer-body">
        <section className="anchor">
          <div className="sec-label">不可改写的基石定义</div>
          <Markdown text={node.strict_definition} />
        </section>

        {node.intuition && (
          <section>
            <div className="sec-label">直觉</div>
            <Markdown text={node.intuition} />
          </section>
        )}

        {node.core_mechanics && (
          <section>
            <div className="sec-label">核心机理</div>
            <Markdown text={node.core_mechanics} />
          </section>
        )}

        {node.key_formulas.length > 0 && (
          <section>
            <div className="sec-label">关键公式</div>
            <ul className="formula-list">
              {node.key_formulas.map((f, i) => (
                <li key={i}>
                  <Markdown text={`$${f}$`} />
                </li>
              ))}
            </ul>
          </section>
        )}

        {node.boundary && (
          <section>
            <div className="sec-label">适用边界</div>
            <Markdown text={node.boundary} />
          </section>
        )}

        {node.prerequisite_refs.length > 0 && (
          <section>
            <div className="sec-label">前置概念</div>
            <div className="chip-row">
              {node.prerequisite_refs.map((r) => (
                <span key={r} className="chip">
                  {r}
                </span>
              ))}
            </div>
          </section>
        )}

        <hr className="divider" />

        <div className="sec-label exercise-heading">
          配套习题 · 同一套推理的不同写法（{exercises.length}）
        </div>

        {exercises.length === 0 && <div className="muted">该节点暂无配套习题。</div>}

        {ex && (
          <div className="exercise">
            <div className="exercise-meta">
              第 {activeIndex + 1} / {exercises.length} 题 · {ex.ex_type}
            </div>
            <div className="exercise-stem">
              <Markdown text={ex.stem} />
            </div>

            <div className="sec-label">解题不变量</div>
            <ol className="inv-list">
              {ex.semantic_invariants.map((s, i) => (
                <li key={i}>
                  <Markdown text={s} />
                </li>
              ))}
            </ol>

            <div className="variant-bar">
              {ex.answers.map((a) => (
                <button
                  key={a.variant_id}
                  className={a.variant_id === variant?.variant_id ? 'variant active' : 'variant'}
                  onClick={() => selectVariant(ex.id, a.variant_id)}
                >
                  {a.style}
                </button>
              ))}
            </div>
            {variant && <div className="variant-register">语调：{variant.register}</div>}

            <div className="answer">
              <Markdown text={variant?.content ?? ''} />
            </div>

            <div className="pager">
              <button
                disabled={activeIndex === 0}
                onClick={() => setActiveIndex(activeIndex - 1)}
              >
                上一题
              </button>
              <button
                disabled={activeIndex >= exercises.length - 1}
                onClick={() => setActiveIndex(activeIndex + 1)}
              >
                下一题
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
