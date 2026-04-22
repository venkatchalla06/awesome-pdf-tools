/**
 * DocViewer — renders spans as paginated document pages (white cards with shadows)
 * matching Draftable's visual style. Also draws scrollbar change markers.
 */
import React, {
  forwardRef, useImperativeHandle, useLayoutEffect,
  useRef, useEffect, useMemo,
} from 'react'
import type { Span } from '../lib/api'

export interface DocViewerHandle {
  scrollTo: (top: number) => void
  getScrollTop: () => number
}

interface Props {
  spans: Span[]
  side: 'original' | 'revised'
  title: string
  zoom: number
  currentChangeIndex: number
  changeSpanIndices: number[]
  onScroll: (top: number) => void
}

const CHARS_PER_PAGE = 3000   // approx characters per simulated page
const MARKER_COLORS: Record<string, string> = {
  delete:    '#ef4444',
  insert:    '#22c55e',
  replace:   '#f59e0b',
  move_from: '#a855f7',
  move_to:   '#06b6d4',
}

/** Split flat span list into "pages" of ~CHARS_PER_PAGE characters */
function paginateSpans(spans: Span[]): Span[][] {
  const pages: Span[][] = []
  let current: Span[] = []
  let charCount = 0

  for (const span of spans) {
    current.push(span)
    charCount += span.text.length
    if (charCount >= CHARS_PER_PAGE && span.text.includes('\n')) {
      pages.push(current)
      current = []
      charCount = 0
    }
  }
  if (current.length) pages.push(current)
  return pages.length ? pages : [[]]
}

const DocViewer = forwardRef<DocViewerHandle, Props>(function DocViewer(
  { spans, side, title, zoom, currentChangeIndex, changeSpanIndices, onScroll },
  ref,
) {
  const scrollRef  = useRef<HTMLDivElement>(null)
  const canvasRef  = useRef<HTMLCanvasElement>(null)
  const spanRefs   = useRef<Map<number, HTMLSpanElement>>(new Map())

  useImperativeHandle(ref, () => ({
    scrollTo:     (top) => { if (scrollRef.current) scrollRef.current.scrollTop = top },
    getScrollTop: ()    => scrollRef.current?.scrollTop ?? 0,
  }))

  /* Scroll active change into view */
  useEffect(() => {
    const spanIdx = changeSpanIndices[currentChangeIndex]
    const el = spanRefs.current.get(spanIdx)
    if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [currentChangeIndex, changeSpanIndices])

  /* Draw scrollbar markers */
  const drawMarkers = () => {
    const canvas = canvasRef.current
    const pane   = scrollRef.current
    if (!canvas || !pane) return
    const { scrollHeight, clientHeight } = pane
    canvas.height = clientHeight
    canvas.width  = 14
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, 14, clientHeight)

    const CHANGE_SET = new Set(['insert','delete','replace','move_from','move_to'])
    spanRefs.current.forEach((el, idx) => {
      const span = spans[idx]
      if (!span || !CHANGE_SET.has(span.type)) return
      const markerY = Math.round((el.offsetTop / scrollHeight) * clientHeight)
      const isActive = changeSpanIndices[currentChangeIndex] === idx
      ctx.fillStyle = isActive ? '#2563eb' : (MARKER_COLORS[span.type] ?? '#94a3b8')
      const h = isActive ? 8 : 4
      ctx.fillRect(isActive ? 0 : 2, Math.max(0, markerY - h/2), 14, h)
    })
  }

  useLayoutEffect(drawMarkers)

  const pages = useMemo(() => paginateSpans(spans), [spans])

  /* Build a flat spanIndex → page mapping to set refs */
  let globalSpanIdx = 0

  return (
    <div className="flex flex-col h-full" style={{ minWidth: 0 }}>
      {/* Pane header */}
      <div className="flex items-center px-4 py-2 bg-[#2d3748] border-b border-[#1a202c] flex-shrink-0">
        <span className="text-xs font-semibold text-slate-300 truncate">{title}</span>
      </div>

      {/* Scroll + markers */}
      <div className="flex-1 relative overflow-hidden">
        <div
          ref={scrollRef}
          className="pane-scroll absolute inset-0"
          style={{ paddingRight: '14px' }}
          onScroll={() => { onScroll(scrollRef.current?.scrollTop ?? 0); drawMarkers() }}
        >
          {pages.map((pageSpans, pageIdx) => {
            const pageContent = pageSpans.map((span) => {
              const idx = globalSpanIdx++
              if (!span.text) return null

              const isChange = span.type !== 'equal'
              const isActive = isChange && changeSpanIndices[currentChangeIndex] === idx

              const cls = [
                span.type === 'delete'    && side === 'original' ? 'diff-delete'    : '',
                span.type === 'insert'    && side === 'revised'  ? 'diff-insert'    : '',
                span.type === 'replace'                          ? 'diff-replace'   : '',
                span.type === 'move_from' && side === 'original' ? 'diff-move-from' : '',
                span.type === 'move_to'   && side === 'revised'  ? 'diff-move-to'   : '',
                isActive                                         ? 'change-active'  : '',
              ].filter(Boolean).join(' ')

              return (
                <span
                  key={idx}
                  className={cls || undefined}
                  title={span.context || undefined}
                  ref={isChange ? (el) => {
                    if (el) spanRefs.current.set(idx, el)
                    else spanRefs.current.delete(idx)
                  } : undefined}
                >
                  {span.text}
                </span>
              )
            })

            return (
              <div
                key={pageIdx}
                className="doc-page"
                style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
              >
                {/* Page number badge */}
                <div className="absolute top-2 right-3 text-[10px] text-gray-300 select-none">
                  p.{pageIdx + 1}
                </div>
                {pageContent}
              </div>
            )
          })}
          <div className="h-8" />
        </div>

        {/* Scrollbar markers */}
        <canvas ref={canvasRef} className="marker-rail" style={{ height: '100%' }} />
      </div>
    </div>
  )
})

export default DocViewer
