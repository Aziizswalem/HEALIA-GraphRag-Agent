'use client'

import { ButtonBlock as ButtonBlockType } from '../../types'
import { ArrowRight } from 'lucide-react'

type Props = { block: ButtonBlockType; isDark: boolean; onAction?: (action: string) => void }

export default function ButtonBlock({ block, isDark, onAction }: Props) {
    return (
        <button
            onClick={() => onAction?.(block.action)}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-xl border transition-all hover:scale-105 active:scale-95 ${
                isDark
                    ? 'bg-gray-800 border-healia-teal/30 text-healia-teal hover:bg-gray-700 hover:border-healia-teal'
                    : 'bg-white border-healia-teal/50 text-healia-teal hover:bg-healia-teal/10'
            }`}
        >
            {block.label}
            <ArrowRight className="h-3.5 w-3.5" />
        </button>
    )
}
