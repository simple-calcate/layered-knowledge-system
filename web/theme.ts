/** X 轴（问题类型）用色标区分列；Y 轴（追问层次）用底色深浅区分层。 */
export const COLUMN_COLORS: Record<number, string> = {
  1: '#2563eb',
  2: '#7c3aed',
  3: '#0891b2',
  4: '#059669',
}

export const FALLBACK_COLOR = '#64748b'

export const columnColor = (x: number) => COLUMN_COLORS[x] || FALLBACK_COLOR

export const DEPTH_TINT: Record<number, string> = {
  1: '#f8fafc',
  2: '#fffdf7',
  3: '#f7f5ff',
}
