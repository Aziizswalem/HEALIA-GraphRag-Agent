'use client'

import { GenuiBlock } from '../../types'
import ChartBlock from './ChartBlock'
import CardBlock from './CardBlock'
import TableBlock from './TableBlock'
import FormBlock from './FormBlock'
import ButtonBlock from './ButtonBlock'
import CanvasBlock from './CanvasBlock'
import InteractiveGraphBlock from './InteractiveGraphBlock'

type Props = {
    block: GenuiBlock
    isDark: boolean
    onFormSubmit?: (values: Record<string, any>) => void
    onAction?: (action: string) => void
}

export default function GenUIRenderer({ block, isDark, onFormSubmit, onAction }: Props) {
    if (!block || !block.type) return null

    switch (block.type) {
        case 'chart':
            return <ChartBlock block={block} isDark={isDark} />
        case 'card':
            return <CardBlock block={block} isDark={isDark} />
        case 'table':
            return <TableBlock block={block} isDark={isDark} />
        case 'form':
            return <FormBlock block={block} isDark={isDark} onSubmit={onFormSubmit} />
        case 'button':
            return <ButtonBlock block={block} isDark={isDark} onAction={onAction} />
        case 'canvas':
            return <CanvasBlock block={block} isDark={isDark} onFormSubmit={onFormSubmit} onAction={onAction} />
        case 'graph':
            return <InteractiveGraphBlock block={block} isDark={isDark} />
        default:
            return null
    }
}
