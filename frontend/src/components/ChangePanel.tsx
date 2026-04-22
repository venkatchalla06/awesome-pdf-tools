/**
 * ChangePanel — right sidebar with filter bar + change list (Draftable-style)
 */
import React, { useState } from 'react'
import { MessageSquare, ChevronDown, ChevronUp, Check, Filter } from 'lucide-react'
export type NoteEntry = { note: string; tag: string }
export type Notes = Record<string, NoteEntry>

type FilterType = 'all' | 'insert' | 'delete' | 'replace' | 'move_from'

const TAG_OPTIONS = [
  { value: '',          label: 'None',      cls: 'bg-gray-100 text-gray-500' },
  { value: 'important', label: '🔴 Important', cls: 'bg-red-100 text-red-700' },
  { value: 'approved',  label: '✅ Approved',  cls: 'bg-green-100 text-green-700' },
  { value: 'rejected',  label: '❌ Rejected',  cls: 'bg-orange-100 text-orange-700' },
  { value: 'question',  label: '❓ Question',  cls: 'bg-blue-100 text-blue-700' },
]
const TAG_CLS: Record<string, string> = {
  important: 'bg-red-100 text-red-700',
  approved:  'bg-green-100 text-green-700',
  rejected:  'bg-orange-100 text-orange-700',
  question:  'bg-blue-100 text-blue-700',
}

export interface Change {
  index: number
  spanIdx: number
  type: 'insert' | 'delete' | 'replace' | 'move_from' | 'move_to'
  preview: string
}

const TYPE_META: Record<string, { label: string; dot: string; badge: string }> = {
  insert:    { label: 'Insertion',  dot: '#22c55e', badge: 'bg-green-100 text-green-800' },
  delete:    { label: 'Deletion',   dot: '#ef4444', badge: 'bg-red-100 text-red-800' },
  replace:   { label: 'Modified',   dot: '#f59e0b', badge: 'bg-amber-100 text-amber-800' },
  move_from: { label: 'Moved',      dot: '#a855f7', badge: 'bg-purple-100 text-purple-800' },
  move_to:   { label: 'Moved to',   dot: '#06b6d4', badge: 'bg-cyan-100 text-cyan-800' },
}

interface Props {
  summary: { additions: number; deletions: number; modifications: number; moves: number; total: number }
  changes: Change[]
  currentChangeIndex: number
  notes: Notes
  onNavigate: (i: number) => void
  onNoteChange: (spanIdx: number, entry: NoteEntry) => void
}

export default function ChangePanel({
  summary, changes, currentChangeIndex, notes, onNavigate, onNoteChange,
}: Props) {
  const [filter,   setFilter]   = useState<FilterType>('all')
  const [expanded, setExpanded] = useState<number | null>(null)

  const filtered = changes.filter(c =>
    filter === 'all' ? true :
    filter === 'move_from' ? (c.type === 'move_from' || c.type === 'move_to') :
    c.type === filter
  )

  const FILTER_PILLS: { key: FilterType; label: string; count: number; color: string; bg: string }[] = [
    { key:'all',       label:'All',       count: summary.total,         color:'#64748b', bg:'#f1f5f9' },
    { key:'insert',    label:'Insertions',count: summary.additions,     color:'#16a34a', bg:'#dcfce7' },
    { key:'delete',    label:'Deletions', count: summary.deletions,     color:'#dc2626', bg:'#fee2e2' },
    { key:'replace',   label:'Modified',  count: summary.modifications, color:'#d97706', bg:'#fef3c7' },
    { key:'move_from', label:'Moved',     count: summary.moves ?? 0,    color:'#9333ea', bg:'#f3e8ff' },
  ]

  return (
    <div className="flex flex-col h-full bg-white">

      {/* Header */}
      <div className="px-4 py-3 border-b bg-[#1e3a5f]">
        <div className="flex items-center gap-2 mb-1">
          <Filter className="w-3.5 h-3.5 text-blue-300" />
          <span className="text-xs font-bold text-white uppercase tracking-wide">Changes</span>
          <span className="ml-auto text-xs font-mono text-blue-200 font-bold">{summary.total}</span>
        </div>
      </div>

      {/* Filter pills */}
      <div className="px-3 py-2.5 border-b bg-gray-50 flex flex-col gap-1.5">
        {FILTER_PILLS.filter(p => p.count > 0 || p.key === 'all').map(p => (
          <button
            key={p.key}
            onClick={() => setFilter(p.key)}
            style={{
              color: filter === p.key ? p.color : '#6b7280',
              background: filter === p.key ? p.bg : 'transparent',
              borderColor: filter === p.key ? p.color : 'transparent',
            }}
            className="filter-pill w-full justify-between"
          >
            <span className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ background: filter === p.key ? p.color : '#d1d5db' }}
              />
              {p.label}
            </span>
            <span className="font-bold tabular-nums">{p.count}</span>
          </button>
        ))}
      </div>

      {/* Change list */}
      <div className="flex-1 overflow-auto divide-y divide-gray-100">
        {filtered.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-xs">No changes match this filter</div>
        ) : (
          filtered.map((change) => {
            const globalIdx   = changes.indexOf(change)
            const isActive    = globalIdx === currentChangeIndex
            const meta        = TYPE_META[change.type] ?? TYPE_META.replace
            const noteKey     = String(change.spanIdx)
            const noteData    = notes[noteKey] ?? { note: '', tag: '' }
            const isOpen      = expanded === change.spanIdx
            const hasAnnotation = noteData.note || noteData.tag

            return (
              <div
                key={change.spanIdx}
                className={`transition-colors ${isActive
                  ? 'bg-blue-50 border-l-4 border-blue-500'
                  : 'border-l-4 border-transparent hover:bg-gray-50'
                }`}
              >
                {/* Main row */}
                <button
                  onClick={() => onNavigate(globalIdx)}
                  className="w-full text-left px-3 py-2.5 flex items-start gap-2.5"
                >
                  {/* Type dot */}
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0 mt-1.5"
                    style={{ background: meta.dot }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${meta.badge}`}>
                        {meta.label}
                      </span>
                      {noteData.tag && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${TAG_CLS[noteData.tag] ?? ''}`}>
                          {noteData.tag}
                        </span>
                      )}
                      {noteData.note && (
                        <MessageSquare className="w-2.5 h-2.5 text-blue-400 flex-shrink-0" />
                      )}
                    </div>
                    <p className="text-xs text-gray-600 leading-relaxed line-clamp-2">
                      {change.preview}
                    </p>
                  </div>
                  {isActive && (
                    <span className="text-blue-500 text-xs font-bold flex-shrink-0">▶</span>
                  )}
                </button>

                {/* Expand note */}
                <button
                  onClick={() => setExpanded(isOpen ? null : change.spanIdx)}
                  className="w-full flex items-center gap-1 px-3 pb-2 text-[10px] text-gray-400 hover:text-gray-600"
                >
                  <MessageSquare className="w-2.5 h-2.5" />
                  {isOpen ? 'Hide note' : 'Note / Tag'}
                  {isOpen ? <ChevronUp className="w-2.5 h-2.5 ml-auto" /> : <ChevronDown className="w-2.5 h-2.5 ml-auto" />}
                </button>

                {isOpen && (
                  <div className="px-3 pb-3 bg-gray-50 border-t border-gray-100">
                    <div className="flex flex-wrap gap-1 mt-2 mb-2">
                      {TAG_OPTIONS.map(opt => (
                        <button
                          key={opt.value}
                          onClick={() => onNoteChange(change.spanIdx, { ...noteData, tag: opt.value })}
                          className={`text-[10px] px-2 py-0.5 rounded-full border transition font-medium
                            ${noteData.tag === opt.value
                              ? opt.cls + ' border-current'
                              : 'bg-white border-gray-200 text-gray-500 hover:border-gray-400'}`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                    <textarea
                      rows={2}
                      placeholder="Add a note…"
                      value={noteData.note}
                      onChange={e => onNoteChange(change.spanIdx, { ...noteData, note: e.target.value })}
                      className="w-full text-xs border border-gray-200 rounded p-1.5 resize-none
                        focus:outline-none focus:border-blue-400 bg-white"
                    />
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* Footer: annotated count */}
      {Object.keys(notes).length > 0 && (
        <div className="px-4 py-2 border-t bg-gray-50 text-[10px] text-gray-400">
          {Object.keys(notes).length} annotated change{Object.keys(notes).length !== 1 ? 's' : ''}
          <span className="ml-1 text-gray-300">· auto-saved</span>
        </div>
      )}
    </div>
  )
}
