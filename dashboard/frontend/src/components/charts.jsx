import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, Line, LineChart, ReferenceArea, ReferenceDot, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { fmt, fmtSigned } from '../api'
import { useChartColors } from '../hooks'
import { Legend } from './ui'

const axisProps = (c) => ({ stroke: c.grid, tick: { fill: c['text-2'], fontSize: 12 }, tickLine: false })

function TipBox({ title, rows }) {
  return (
    <div className="tip">
      <div className="tip-title">{title}</div>
      {rows.map((r) => (
        <div className="tip-row" key={r.label}>
          <span className="tip-mark" style={{ background: r.color }} />
          <span className="tip-label">{r.label}</span>
          <span className="tip-value">{r.value}</span>
        </div>
      ))}
    </div>
  )
}

// ------------------------------------------------------------------ từ bị từ điển tổng quát gắn "tiêu cực"
export function MisclassifiedBars({ words, legend = true }) {
  const c = useChartColors()
  const data = words.map((w) => ({ ...w, label: w.word }))
  return (
    <>
      {legend && <MisclassifiedLegend />}
      <div className="chart" style={{ height: 36 + data.length * 30 }}>
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 56, bottom: 4, left: 8 }} barCategoryGap={6}>
            <XAxis type="number" hide domain={[0, 'dataMax']} />
            <YAxis type="category" dataKey="label" width={96} {...axisProps(c)} axisLine={false} tick={{ fill: c.text, fontSize: 13 }} />
            <Tooltip cursor={{ fill: c.band }} content={({ active, payload }) => active && payload?.length ? (
              <TipBox title={`“${payload[0].payload.word}”`} rows={[{
                label: payload[0].payload.in_fin_negative ? 'Tiêu cực thật' : 'Gán sai',
                color: payload[0].payload.in_fin_negative ? c.accent : c.noise,
                value: `${fmt(payload[0].value, 2)}% số lần gắn nhãn`,
              }]} />
            ) : null} />
            <Bar dataKey="share_pct" radius={[0, 4, 4, 0]} isAnimationActive={false}>
              {data.map((d) => <Cell key={d.word} fill={d.in_fin_negative ? c.accent : c.noise} />)}
              <LabelList dataKey="share_pct" position="right" formatter={(v) => `${fmt(v, 1)}%`} fill={c['text-2']} fontSize={12} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

export function MisclassifiedLegend() {
  const c = useChartColors()
  return (
    <Legend items={[
      { label: 'Không tiêu cực trong tài chính (gán sai)', color: c.noise, box: true },
      { label: 'Tiêu cực thật (có trong từ điển tài chính)', color: c.accent, box: true },
    ]} />
  )
}

// ------------------------------------------------------------------ CAAR theo nhóm giọng điệu
export function CaarChart({ data }) {
  const c = useChartColors()
  const color = { T1: c.neg, T2: c.neutral, T3: c.pos }
  const last = data.rows[data.rows.length - 1] || {}
  // giãn nhãn cuối đường để không chồng nhau
  const order = data.groups.map((g) => ({ ...g, v: last[g.key] })).sort((a, b) => a.v - b.v)
  const vals = data.rows.flatMap((r) => data.groups.map((g) => r[g.key]))
  const lo = Math.floor(Math.min(0, ...vals) * 2) / 2, hi = Math.ceil(Math.max(0, ...vals) * 2) / 2
  const yTicks = [...Array(Math.round((hi - lo) * 2) + 1).keys()].map((i) => lo + i / 2)
  // nhãn cuối đường: giãn tối thiểu 8% chiều cao trục để không chồng nhau
  const gap = 0.08 * (hi - lo), lastX = data.rows[data.rows.length - 1]?.phien
  const labels = order.map((g) => ({ ...g, y: g.v }))
  for (let k = 1; k < labels.length; k++) labels[k].y = Math.max(labels[k].y, labels[k - 1].y + gap)
  return (
    <>
      <Legend items={data.groups.map((g) => ({ label: `${g.label} (n = ${g.n})`, color: color[g.key], dashed: g.key === 'T2' }))} />
      <div className="chart" style={{ height: 340 }}>
        <ResponsiveContainer>
          <LineChart data={data.rows} margin={{ top: 12, right: 88, bottom: 18, left: -4 }}>
            <CartesianGrid stroke={c.grid} vertical={false} />
            <ReferenceArea x1={0} x2={3} fill={c.band} fillOpacity={1} ifOverflow="extendDomain"
              label={{ value: 'Cửa sổ chính [0, 3]', position: 'insideTop', fill: c['text-2'], fontSize: 11 }} />
            <XAxis dataKey="phien" type="number" domain={['dataMin', 'dataMax']} ticks={[-10, -5, 0, 3, 5, 10]} {...axisProps(c)}
              label={{ value: 'Phiên giao dịch so với ngày công bố (T = 0)', position: 'insideBottom', offset: -10, fill: c['text-2'], fontSize: 12 }} />
            <YAxis {...axisProps(c)} domain={[lo, hi]} ticks={yTicks} tickFormatter={(v) => `${fmt(v, 1)}%`} width={56} />
            <ReferenceLine y={0} stroke={c.muted} />
            <ReferenceLine x={0} stroke={c.muted} />
            <Tooltip cursor={{ stroke: c.muted }} content={({ active, payload, label }) => active && payload?.length ? (
              <TipBox title={`Phiên T${label >= 0 ? '+' : ''}${label}`} rows={[...payload].sort((a, b) => b.value - a.value).map((p) => ({
                label: data.groups.find((g) => g.key === p.dataKey)?.label, color: color[p.dataKey], value: `${fmtSigned(p.value, 2)}%`,
              }))} />
            ) : null} />
            {data.groups.map((g) => (
              <Line key={g.key} dataKey={g.key} stroke={color[g.key]} strokeWidth={2} dot={false} isAnimationActive={false}
                strokeDasharray={g.key === 'T2' ? '6 4' : undefined} activeDot={{ r: 5, stroke: c.surface, strokeWidth: 2 }}
              />
            ))}
            {labels.map((g) => (
              <ReferenceDot key={g.key} x={lastX} y={g.y} r={0} ifOverflow="visible"
                label={{ value: g.label.replace(/^T\d /, ''), position: 'right', fill: c.text, fontSize: 12, fontWeight: 600 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-foot">
        Lợi suất bất thường trung bình cộng dồn từ phiên T−10. Cuối cửa sổ (T+10): {order.map((g) => `${g.label.replace(/^T\d /, '')} ${fmtSigned(g.v, 2)}%`).join(' · ')}.
      </p>
    </>
  )
}

// ------------------------------------------------------------------ hệ số + khoảng tin cậy 95% (vẽ tay bằng SVG)
export function CoefPlot({ rows }) {
  const c = useChartColors()
  const W = 640, rowH = 34, top = 28, labelW = 190, valueW = 120, plotW = W - labelW - valueW - 16
  const ext = Math.max(...rows.flatMap((r) => [Math.abs(r.lo_pp), Math.abs(r.hi_pp)]), 0.5) * 1.1
  const x = (v) => labelW + ((v + ext) / (2 * ext)) * plotW
  const H = top + rows.length * rowH + 30
  const step = ext > 1.5 ? 1 : 0.5
  const ticks = []
  for (let t = -Math.floor(ext / step) * step; t <= ext; t += step) ticks.push(+t.toFixed(2))
  return (
    <div className="coefplot">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Hệ số tone tiêu cực theo từng cửa sổ, kèm khoảng tin cậy 95%">
        <text x={x(-ext)} y={14} fill={c['text-2']} fontSize={11}>← CAR thấp hơn</text>
        <text x={x(ext)} y={14} fill={c['text-2']} fontSize={11} textAnchor="end">CAR cao hơn →</text>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={top - 6} y2={H - 26} stroke={t === 0 ? c.muted : c.grid} strokeWidth={t === 0 ? 1.5 : 1} />
            <text x={x(t)} y={H - 10} fill={c['text-2']} fontSize={11} textAnchor="middle">{fmtSigned(t, step < 1 ? 1 : 0)}</text>
          </g>
        ))}
        {rows.map((r, i) => {
          const y = top + i * rowH + rowH / 2
          const sig = Boolean(r.stars)
          const col = r.placebo ? c.muted : sig ? c.neg : c['text-2']
          return (
            <g key={r.label}>
              <title>{`${r.label}: ${fmtSigned(r.coef_pp, 2)} điểm % (KTC 95%: ${fmtSigned(r.lo_pp, 2)} đến ${fmtSigned(r.hi_pp, 2)}) – ${r.sig}`}</title>
              {r.main && <rect x={0} y={y - rowH / 2 + 2} width={W} height={rowH - 4} rx={6} fill={c.band} />}
              <text x={8} y={y + 4} fill={c.text} fontSize={13} fontWeight={r.main ? 700 : 400} fontStyle={r.placebo ? 'italic' : 'normal'}>{r.label}</text>
              <line x1={x(r.lo_pp)} x2={x(r.hi_pp)} y1={y} y2={y} stroke={col} strokeWidth={2} strokeLinecap="round" />
              <circle cx={x(r.coef_pp)} cy={y} r={5.5} fill={sig ? col : c.surface} stroke={col} strokeWidth={2} />
              <text x={W - 8} y={y + 4} fill={c.text} fontSize={13} textAnchor="end" fontWeight={sig ? 700 : 400}>
                {fmtSigned(r.coef_pp, 2)}{r.stars ? ` ${r.stars}` : ''}
              </text>
            </g>
          )
        })}
      </svg>
      <Legend items={[
        { label: 'Có ý nghĩa thống kê (khoảng tin cậy không chứa 0)', color: c.neg },
        { label: 'Không có ý nghĩa (khoảng tin cậy cắt qua 0)', color: c['text-2'] },
      ]} />
    </div>
  )
}

// ------------------------------------------------------------------ thanh ngang đơn giản (phễu mẫu, CER…)
export function SimpleBars({ items, max, unit = '', digits = 0, color }) {
  const c = useChartColors()
  const top = max ?? Math.max(...items.map((i) => i.value))
  return (
    <ul className="hbars">
      {items.map((it) => (
        <li key={it.label} className={it.indent ? 'indent' : ''}>
          <span className="hbar-label">{it.label}</span>
          <span className="hbar-track">
            <span className="hbar-fill" style={{ width: `${Math.max(0.5, (100 * it.value) / top)}%`, background: it.color || color || c.accent }} />
          </span>
          <span className="hbar-value">{fmt(it.value, digits)}{unit}</span>
        </li>
      ))}
    </ul>
  )
}

// ------------------------------------------------------------------ 2 thị trường cùng một chỉ số theo năm (cùng đơn vị → 1 trục)
export function MarketYearLines({ vn, us, dataKey, unit = '%', digits = 2, height = 300 }) {
  const c = useChartColors()
  const years = [...new Set([...vn, ...us].map((r) => r.year))].sort((a, b) => a - b)
  const get = (rows, y) => rows.find((r) => r.year === y)
  const data = years.map((y) => ({ year: y, vn: get(vn, y)?.[dataKey] ?? null, us: get(us, y)?.[dataKey] ?? null, nvn: get(vn, y)?.N, nus: get(us, y)?.N }))
  const max = Math.max(...data.flatMap((d) => [d.vn ?? 0, d.us ?? 0]))
  const top = Math.ceil(max * 2) / 2
  const ticks = [...Array(Math.round(top * 2) + 1).keys()].map((i) => i / 2)
  const series = [{ key: 'vn', label: 'Việt Nam', color: c.vn }, { key: 'us', label: 'Mỹ', color: c.us }]
  const lastOf = (k) => [...data].reverse().find((d) => d[k] != null)
  return (
    <>
      <Legend items={series.map((s) => ({ label: s.label, color: s.color }))} />
      <div className="chart" style={{ height }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 12, right: 72, bottom: 4, left: -8 }}>
            <CartesianGrid stroke={c.grid} vertical={false} />
            <XAxis dataKey="year" {...axisProps(c)} />
            <YAxis {...axisProps(c)} domain={[0, top]} ticks={ticks} tickFormatter={(v) => `${fmt(v, 1)}${unit}`} width={52} />
            <Tooltip cursor={{ stroke: c.muted }} content={({ active, payload, label }) => active && payload?.length ? (
              <TipBox title={`Năm ${label}`} rows={payload.filter((p) => p.value != null).map((p) => ({
                label: `${p.dataKey === 'vn' ? 'Việt Nam' : 'Mỹ'} (${p.payload[p.dataKey === 'vn' ? 'nvn' : 'nus']} văn bản)`,
                color: p.dataKey === 'vn' ? c.vn : c.us, value: `${fmt(p.value, digits)}${unit}`,
              }))} />
            ) : null} />
            {series.map((s) => (
              <Line key={s.key} dataKey={s.key} stroke={s.color} strokeWidth={2} connectNulls={false} isAnimationActive={false}
                dot={{ r: 3.5, fill: s.color, strokeWidth: 0 }} activeDot={{ r: 5.5, stroke: c.surface, strokeWidth: 2 }} />
            ))}
            {series.map((s) => { const l = lastOf(s.key); return l && (
              <ReferenceDot key={s.key} x={l.year} y={l[s.key]} r={0} ifOverflow="visible"
                label={{ value: s.label, position: 'right', fill: c.text, fontSize: 12, fontWeight: 600 }} />
            ) })}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

// ------------------------------------------------------------------ độ phủ kho tin CafeF theo tháng (tô tháng hổng)
export function NewsCoverageChart({ rows, threshold, exclude }) {
  const c = useChartColors()
  const data = rows.filter((r) => r.so_ma >= 10 && r.thang !== exclude)
  const firstOfYear = data.filter((r) => r.thang.endsWith('-01')).map((r) => r.thang)
  const gaps = data.filter((r) => r.hong).map((r) => r.thang)
  return (
    <>
      <Legend items={[
        { label: 'Tháng bình thường', color: c.accent, box: true },
        { label: 'Tháng kho tin bị hổng', color: c.neg, box: true },
        { label: 'Ngưỡng hổng (25% trung vị)', color: c.muted, dashed: true },
      ]} />
      <div className="chart" style={{ height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -12 }} barCategoryGap={1}>
            <CartesianGrid stroke={c.grid} vertical={false} />
            <XAxis dataKey="thang" ticks={firstOfYear} tickFormatter={(v) => v.slice(0, 4)} {...axisProps(c)} interval={0} />
            <YAxis {...axisProps(c)} width={44} tickFormatter={(v) => fmt(v, 0)} />
            <Tooltip cursor={{ fill: c.band }} content={({ active, payload }) => active && payload?.length ? (
              <TipBox title={`Tháng ${payload[0].payload.thang.split('-').reverse().join('/')}`} rows={[
                { label: 'Tin / mã', color: payload[0].payload.hong ? c.neg : c.accent, value: fmt(payload[0].payload.tin_moi_ma, 1) },
                { label: 'Tổng số tin', color: 'transparent', value: fmt(payload[0].payload.so_tin, 0) },
                { label: 'Số mã đã thu thập', color: 'transparent', value: fmt(payload[0].payload.so_ma, 0) },
              ]} />
            ) : null} />
            {threshold != null && <ReferenceLine y={threshold} stroke={c.muted} strokeDasharray="5 4" />}
            {gaps.length > 0 && (
              <ReferenceArea x1={gaps[0]} x2={gaps[gaps.length - 1]} fill={c.neg} fillOpacity={0.12} ifOverflow="extendDomain"
                label={{ value: `Hổng ${gaps.map((g) => g.slice(5)).join('–')}/${gaps[0].slice(0, 4)}`, position: 'insideTop', fill: c.text, fontSize: 11, fontWeight: 600 }} />
            )}
            <Bar dataKey="tin_moi_ma" isAnimationActive={false} radius={[2, 2, 0, 0]}>
              {data.map((d) => <Cell key={d.thang} fill={d.hong ? c.neg : c.accent} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}
