'use client'

import { TableBlock as TableBlockType } from '../../types'
import {
    Table,
    TableHead,
    TableHeaderCell,
    TableBody,
    TableRow,
    TableCell,
} from '@tremor/react'
import { AlertCircle, CheckCircle, Clock, Database } from 'lucide-react'

type Props = { block: TableBlockType; isDark: boolean }

const COLUMN_LABELS: Record<string, string> = {
    assure_id: 'ID Assuré',
    nom: 'Nom',
    prenom: 'Prénom',
    date_soin: 'Date du Soin',
    reste_plafond: 'Dépassement Plafond',
    num_bs: 'N° Bulletin',
    discipline: 'Discipline',
    disciplines: 'Disciplines & Prestations',
    depense_totale: 'Dépense Totale',
    prise_en_charge: 'Prise en Charge',
    reste_a_charge: 'Reste à Charge',
    montant_depense: 'Dépense',
    montant_rembourse: 'Remboursement',
    etat: 'Statut',
    date_radiation: 'Date Radiation',
    bs_id: 'ID Bulletin',
    validation_date: 'Validation',
    delai_post_radiation: 'Délai Post-Radiation',
}

function formatCell(column: string, value: any, isDark: boolean) {
    if (value === null || value === undefined) return '-'

    // Spécifique délai post-radiation
    if (column === 'delai_post_radiation') {
        return (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-500/15 text-amber-500 border border-amber-500/30">
                <Clock className="h-3 w-3" />
                {String(value)}
            </span>
        )
    }

    // Spécifique date de radiation
    if (column === 'date_radiation') {
        return (
            <span className="inline-flex items-center gap-1 text-xs font-mono font-semibold text-rose-500 dark:text-rose-400">
                {String(value)}
            </span>
        )
    }

    // Spécifique dépassement plafond (reste_plafond négatif)
    if (column === 'reste_plafond') {
        const num = typeof value === 'number' ? value : parseFloat(String(value))
        if (!isNaN(num) && num < 0) {
            return (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-rose-500/15 text-rose-500 border border-rose-500/30">
                    <AlertCircle className="h-3 w-3" />
                    {num.toFixed(2)} TND
                </span>
            )
        }
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono font-medium text-emerald-500">
                <CheckCircle className="h-3 w-3" />
                +{num.toFixed(2)} TND
            </span>
        )
    }

    if (column === 'assure_id' || column === 'num_bs' || column === 'bs_id') {
        return (
            <span className={`font-mono font-bold text-xs ${isDark ? 'text-teal-400' : 'text-teal-700'}`}>
                {String(value)}
            </span>
        )
    }

    if (column === 'etat') {
        return (
            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-500/15 text-emerald-500 border border-emerald-500/25">
                {String(value)}
            </span>
        )
    }

    return String(value)
}

export default function TableBlock({ block, isDark }: Props) {
    return (
        <div
            className={`rounded-2xl border overflow-hidden transition-all duration-300 ${isDark ? 'bg-gray-900/80 border-gray-800 shadow-lg shadow-black/30' : 'bg-white border-gray-200/90 shadow-sm'
                }`}
        >
            {block.title && (
                <div
                    className={`flex items-center justify-between px-4 py-3 border-b ${isDark ? 'border-gray-800 bg-gray-950/40' : 'border-gray-100 bg-slate-50/50'
                        }`}
                >
                    <div className="flex items-center gap-2">
                        <Database className="h-3.5 w-3.5 text-teal-500" />
                        <h3 className={`text-xs font-bold tracking-tight uppercase ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>
                            {block.title}
                        </h3>
                    </div>
                    <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded ${isDark ? 'bg-white/10 text-gray-400' : 'bg-slate-200 text-slate-600'
                            }`}
                    >
                        {block.rows.length} lignes
                    </span>
                </div>
            )}

            <div className="overflow-x-auto">
                <Table className="text-xs">
                    <TableHead className={isDark ? 'bg-gray-950/50' : 'bg-slate-50/80'}>
                        <TableRow>
                            {block.columns.map((col) => (
                                <TableHeaderCell
                                    key={col}
                                    className={`text-[11px] font-bold uppercase tracking-wider py-2.5 ${isDark ? 'text-gray-400' : 'text-gray-600'
                                        }`}
                                >
                                    {COLUMN_LABELS[col] || col}
                                </TableHeaderCell>
                            ))}
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {block.rows.map((row, i) => (
                            <TableRow
                                key={i}
                                className={`transition-colors ${isDark ? 'hover:bg-gray-800/50' : 'hover:bg-teal-50/30'
                                    }`}
                            >
                                {block.columns.map((col) => (
                                    <TableCell key={col} className="py-2.5">
                                        {formatCell(col, row[col], isDark)}
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </div>
    )
}
