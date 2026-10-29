export function AxisChip({
  data,
}: {
  data: { text: string; sub?: string; kind: 'col' | 'row' }
}) {
  return (
    <div className={`axis-chip axis-${data.kind}`}>
      <div className="axis-title">{data.text}</div>
      {data.sub ? <div className="axis-desc">{data.sub}</div> : null}
    </div>
  )
}

export function BlankCell({ data }: { data: { text: string } }) {
  return <div className="blank-cell">{data.text}</div>
}
