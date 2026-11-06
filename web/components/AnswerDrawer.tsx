import { useKnowledgeStore, useAnswerStore, useCanvasStore } from '../lib/stores'
import { Markdown } from './Markdown'

export function AnswerDrawer({ questionId }: { questionId: string }) {
  const q = useKnowledgeStore((s) => s.questionsById[questionId])
  const concept = useKnowledgeStore((s) => s.corpus?.concept)
  const answerMap = useAnswerStore((s) => s.answerMap)
  const chooseAnswer = useAnswerStore((s) => s.chooseAnswer)
  const closeDrawer = useAnswerStore((s) => s.closeDrawer)
  const selectQuestion = useCanvasStore((s) => s.selectQuestion)

  if (!q) return null

  const canon = q.canonical
  const answers = q.answers
  const answerId = answerMap[q.id] ?? answers[0]?.id
  const answer = answers.find((a) => a.id === answerId) ?? answers[0]

  const close = () => {
    closeDrawer()
    selectQuestion(null)
  }

  return (
    <aside className="drawer">
      <div className="drawer-head">
        <div>
          <span className="coord-chip">X{q.x} Y{q.y}</span>
          <span className="drawer-axis">{q.breadth_label} × {q.depth_label}</span>
        </div>
        <button className="close-btn" onClick={close} aria-label="关闭">×</button>
      </div>

      <div className="origin-block">
        <div className="origin-label">原点 · 一个名词，不预设固定定义</div>
        <div className="origin-term">{concept?.term ?? q.concept_id}</div>
        <div className="origin-summary">{concept?.summary ?? ''}</div>
      </div>

      <h2 className="q-title">{q.text}</h2>
      {q.note ? <p className="q-note">{q.note}</p> : null}

      {!canon ? (
        <div className="empty-state">
          <div className="empty-title">这一格还没有经认定的正确答案</div>
          <p>问题已经问出来了，但还没人写下被审核认可的答案要点。为它补一份 canon，或为已有答案补一条同义改写，都算添砖加瓦。</p>
          <a href="https://github.com/simple-calcate/layered-knowledge-system/blob/main/CONTRIBUTING.md" target="_blank" rel="noreferrer">
            看看怎么贡献 →
          </a>
        </div>
      ) : (
        <>
          <div className="inv-block">
            <div className="section-label">唯一正确的答案 · 必须守住的要点</div>
            <ul className="inv-list">
              {canon.invariants.map((i) => (
                <li key={i.id}><code>{i.id}</code>{i.claim}</li>
              ))}
            </ul>
            <p className="inv-note">
              认定依据：{canon.basis}　·　审核 {canon.review.by}（{canon.review.at}）
            </p>
            <p className="inv-note">下面每一条说法都必须逐条守住这些要点，换了说法但意思不变。</p>
          </div>

          <div className="section-label">换一种说法（意思不变，表达不同）</div>
          <div className="variant-bar">
            {answers.map((a) => (
              <button
                key={a.id}
                className={`variant${a.id === answer?.id ? ' active' : ''}`}
                onClick={() => chooseAnswer(q.id, a.id)}
              >
                {a.style}
              </button>
            ))}
          </div>

          {answer ? (
            <>
              <div className="byline">
                <span className="byline-author">作者 {answer.author.name}</span>
                <span className="byline-sep">·</span>
                <span>语调 {answer.register}</span>
                <span className="byline-sep">·</span>
                <span title={answer.source.note}>出处 {answer.source.note}</span>
              </div>
              {answer.misses.length > 0 ? (
                <div className="reject-note">质检未通过：漏掉要点 {answer.misses.join('、')}</div>
              ) : null}
              <div className="answer"><Markdown text={answer.content} /></div>
            </>
          ) : null}
        </>
      )}

      <div className="drawer-foot">
        问题由 {q.author.name} 提出 · 当前 {q.answer_count} 条同义改写
      </div>
    </aside>
  )
}
