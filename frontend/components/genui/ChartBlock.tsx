'use client'

import { ChartBlock as ChartBlockType } from '../../types'
import {
    BarChart,
    LineChart,
    DonutChart,
    ScatterChart,
} from '@tremor/react'

type Props = { block: ChartBlockType; isDark: boolean }

const CHART_COLORS = ['cyan', 'teal', 'emerald', 'amber', 'rose', 'violet', 'blue']

const isCurrencyMetric = (unit?: string, title?: string, keys: string[] = []): boolean => {
    if (unit === 'count' || unit === 'number') return false
    if (unit === 'currency') return true

    const text = `${title || ''} ${keys.join(' ')}`.toLowerCase()

    // Explicit count indicators
    const countKeywords = [
        'nombre', 'bulletin', 'count', 'effectif', 'quantite', 'quantité',
        'qte', 'nb_', 'cas', 'radiation', 'adherent', 'assuré', 'praticien'
    ]
    const hasCount = countKeywords.some(kw => text.includes(kw))

    // Currency indicators
    const currencyKeywords = [
        'tnd', 'dépense', 'depense', 'rembourse', 'pec', 'montant',
        'solde', 'plafond', 'consommation', 'coût', 'cout', 'tarif', 'prix'
    ]
    const hasCurrency = currencyKeywords.some(kw => text.includes(kw))

    if (hasCount && !hasCurrency) return false
    if (hasCurrency) return true
    return false
}

const formatNumber = (v: number): string => {
    if (Number.isInteger(v)) {
        return v.toLocaleString('fr-FR')
    }
    if (Math.abs(v - Math.round(v)) < 0.01) {
        return Math.round(v).toLocaleString('fr-FR')
    }
    return v.toLocaleString('fr-FR', { maximumFractionDigits: 1 })
}

const formatCurrency = (v: number): string => {
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M TND`
    if (v >= 1_000) return `${(v / 1_000).toFixed(1)}k TND`
    return `${Number.isInteger(v) ? v : v.toFixed(2)} TND`
}

const SERIES_LABELS: Record<string, string> = {
    Depense: 'Dépenses',
    Rembourse: 'Remboursements',
    Bulletins: 'Nombre de Bulletins',
    value: 'Valeur',
}

const seriesLabel = (key: string) => SERIES_LABELS[key] ?? key

const detectCategories = (data: ChartBlockType['data'], xKey: string): string[] => {
    if (!Array.isArray(data) || data.length === 0) return []
    const first = data[0]
    const numeric = Object.keys(first).filter(k => k !== xKey && typeof first[k] === 'number')
    return (numeric.length ? numeric : Object.keys(first).filter(k => k !== xKey)).slice(0, 3)
}

export default function ChartBlock({ block, isDark }: Props) {
    const indexKey = block.xKey || 'name'
    const valueKey = block.yKey || 'value'

    const containerClass = `rounded-2xl border p-4 ${isDark ? 'bg-gray-900/60 border-gray-800' : 'bg-white border-gray-200'}`

    const rawKeys = detectCategories(block.data, indexKey)
    const categories = rawKeys.length ? rawKeys : [valueKey]

    const isCurrency = isCurrencyMetric(
        block.valueUnit,
        block.title,
        [valueKey, ...categories]
    )

    const valueFormatter = isCurrency ? formatCurrency : formatNumber

    const renderChart = () => {
        const common = { className: isDark ? 'text-gray-300' : '' }

        const renderSeriesChart = (type: 'bar' | 'line') => {
            const chartData = block.data.map(row => {
                const out: Record<string, any> = { [indexKey]: row[indexKey] }
                for (const k of categories) out[seriesLabel(k)] = row[k]
                return out
            })
            const props = {
                data: chartData,
                index: indexKey,
                categories: categories.map(seriesLabel),
                colors: CHART_COLORS,
                valueFormatter: valueFormatter,
                yAxisWidth: isCurrency ? 60 : 45,
                showAnimation: true,
                showLegend: categories.length > 1,
                ...common,
            }
            return type === 'bar'
                ? <BarChart {...props} />
                : <LineChart {...props} curveType="monotone" />
        }

        switch (block.chartType) {
            case 'bar':
                return renderSeriesChart('bar')

            case 'line':
                return renderSeriesChart('line')

            case 'pie':
                return (
                    <DonutChart
                        data={block.data}
                        index={indexKey}
                        category={valueKey}
                        colors={CHART_COLORS}
                        valueFormatter={valueFormatter}
                        variant="pie"
                        showAnimation
                        {...common}
                    />
                )

            case 'scatter':
                return (
                    <ScatterChart
                        data={block.data}
                        x={indexKey}
                        y={valueKey}
                        category="category"
                        colors={CHART_COLORS}
                        valueFormatter={{
                            x: (v: number) => String(v),
                            y: valueFormatter,
                        }}
                        showAnimation
                        showLegend={false}
                        {...common}
                    />
                )

            default:
                return <p className="text-sm text-gray-400">Type de graphique non supporté</p>
        }
    }

    return (
        <div className={containerClass}>
            {block.title && (
                <h3 className={`text-sm font-bold mb-3 ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>{block.title}</h3>
            )}
            {renderChart()}
        </div>
    )
}
