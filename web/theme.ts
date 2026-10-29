export const FAMILY_COLORS: Record<string, string> = {
  scalar_core: '#2563eb',
  compute_graph: '#7c3aed',
  jacobian_mode: '#0891b2',
  matrix_layer: '#059669',
  higher_order: '#d97706',
}

export const FALLBACK_COLOR = '#64748b'

export const familyColor = (key: string) => FAMILY_COLORS[key] || FALLBACK_COLOR

export const STRATUM_TINT: Record<number, string> = {
  1: '#f8fafc',
  2: '#ffffff',
  3: '#f6fffb',
  4: '#fffaf3',
  5: '#f7f5ff',
}
