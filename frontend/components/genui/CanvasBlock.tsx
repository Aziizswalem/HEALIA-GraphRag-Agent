'use client'

import { CanvasBlock as CanvasBlockType } from '../../types'
import GenUIRenderer from './GenUIRenderer'

type Props = { block: CanvasBlockType; isDark: boolean; onFormSubmit?: (values: Record<string, any>) => void; onAction?: (action: string) => void }

export default function CanvasBlock({ block, isDark, onFormSubmit, onAction }: Props) {
    return (
        <div className={`rounded-2xl border p-4 ${isDark ? 'bg-gray-900/40 border-gray-800' : 'bg-gray-50 border-gray-200'}`}>
            {block.title && (
                <h3 className={`text-sm font-bold mb-4 ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>{block.title}</h3>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {block.children.map((child, i) => (
                    <GenUIRenderer key={i} block={child} isDark={isDark} onFormSubmit={onFormSubmit} onAction={onAction} />
                ))}
            </div>
        </div>
    )
}
