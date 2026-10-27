'use client'

import { CardBlock as CardBlockType } from '../../types'
import { Card, Badge, Text } from '@tremor/react'
import { ArrowRight, UserCheck, Shield, Wallet, Activity, CheckCircle2 } from 'lucide-react'

type Props = { block: CardBlockType; isDark: boolean }

export default function CardBlock({ block, isDark }: Props) {
    const hasDetailedAdherent = Boolean(block.nom || block.contrat || block.plafond_annuel || block.consommation)

    return (
        <Card
            className={`transition-all duration-300 hover:shadow-md ${
                isDark
                    ? 'bg-gray-900/80 border-gray-800 text-gray-100 shadow-lg shadow-black/30'
                    : 'bg-white border-gray-200/90 text-gray-900 shadow-sm'
            }`}
        >
            {block.image && (
                <div className="h-40 bg-gradient-to-br from-healia-teal/20 to-healia-dark/20 flex items-center justify-center rounded-tremor-default mb-4">
                    <span className="text-4xl opacity-40">📊</span>
                </div>
            )}

            {/* Header: Title + Badge */}
            <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                    {hasDetailedAdherent ? (
                        <div className={`p-1.5 rounded-lg ${isDark ? 'bg-emerald-500/20 text-emerald-400' : 'bg-emerald-50 text-emerald-700'}`}>
                            <UserCheck className="h-4 w-4" />
                        </div>
                    ) : (
                        <div className={`p-1.5 rounded-lg ${isDark ? 'bg-teal-500/20 text-teal-400' : 'bg-teal-50 text-teal-700'}`}>
                            <Activity className="h-4 w-4" />
                        </div>
                    )}
                    <div>
                        <h3 className={`text-sm font-bold tracking-tight ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                            {block.title}
                        </h3>
                        {hasDetailedAdherent && block.nom && block.title !== block.nom && (
                            <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{block.nom}</p>
                        )}
                    </div>
                </div>

                {block.badge && (
                    <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                            block.badge.toLowerCase().includes('actif')
                                ? isDark
                                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                    : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                : block.badge.toLowerCase().includes('alerte') || block.badge.toLowerCase().includes('critique')
                                ? isDark
                                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30 animate-pulse'
                                    : 'bg-rose-100 text-rose-800 border border-rose-200'
                                : isDark
                                ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                                : 'bg-teal-100 text-teal-800 border border-teal-200'
                        }`}
                    >
                        {block.badge.toLowerCase().includes('actif') && <CheckCircle2 className="h-3 w-3" />}
                        {block.badge}
                    </span>
                )}
            </div>

            {/* Description */}
            {block.description && (
                <p className={`mt-2.5 text-xs leading-relaxed ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    {block.description}
                </p>
            )}

            {/* Detailed Adherent KPI Grid */}
            {hasDetailedAdherent && (
                <div className="mt-4 pt-3 border-t border-black/[0.06] dark:border-white/[0.08] space-y-3">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {block.contrat && (
                            <div className={`p-2.5 rounded-xl border ${isDark ? 'bg-black/30 border-white/5' : 'bg-slate-50 border-slate-100'}`}>
                                <span className="text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-1 mb-1">
                                    <Shield className="h-3 w-3 text-teal-500" />
                                    Contrat
                                </span>
                                <span className="font-mono text-xs font-bold text-teal-600 dark:text-teal-400 block truncate">
                                    {block.contrat}
                                </span>
                            </div>
                        )}

                        {block.statut && (
                            <div className={`p-2.5 rounded-xl border ${isDark ? 'bg-black/30 border-white/5' : 'bg-slate-50 border-slate-100'}`}>
                                <span className="text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 block mb-1">
                                    Statut
                                </span>
                                <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 block">
                                    {block.statut}
                                </span>
                            </div>
                        )}

                        {block.plafond_annuel && (
                            <div className={`p-2.5 rounded-xl border ${isDark ? 'bg-black/30 border-white/5' : 'bg-slate-50 border-slate-100'}`}>
                                <span className="text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-1 mb-1">
                                    <Wallet className="h-3 w-3 text-indigo-500" />
                                    Plafond Annuel
                                </span>
                                <span className="font-mono text-xs font-bold text-gray-900 dark:text-gray-100 block">
                                    {block.plafond_annuel}
                                </span>
                            </div>
                        )}

                        {block.consommation && (
                            <div className={`p-2.5 rounded-xl border ${isDark ? 'bg-black/30 border-white/5' : 'bg-slate-50 border-slate-100'}`}>
                                <span className="text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 block mb-1">
                                    Consommation
                                </span>
                                <span className="font-mono text-xs font-bold text-amber-600 dark:text-amber-400 block">
                                    {block.consommation}
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Progress Bar: Consommation vs Plafond (35.4%) */}
                    <div className="pt-1">
                        <div className="flex justify-between text-[11px] font-medium mb-1.5">
                            <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                                Consommation : <strong className="text-amber-500">35.4%</strong> (1 240 TND)
                            </span>
                            <span className="text-emerald-500 font-semibold">
                                Solde disponible : 2 260 TND
                            </span>
                        </div>
                        <div className="h-2 w-full bg-black/10 dark:bg-white/10 rounded-full overflow-hidden p-0.5">
                            <div
                                className="h-full bg-gradient-to-r from-teal-500 via-emerald-400 to-emerald-500 rounded-full transition-all duration-1000 shadow-sm"
                                style={{ width: '35.4%' }}
                            />
                        </div>
                    </div>
                </div>
            )}

            {/* Action CTA */}
            {block.action && (
                <button
                    onClick={() => {
                        if (block.action?.url && block.action.url !== '#') window.open(block.action.url, '_blank')
                    }}
                    className={`mt-3.5 inline-flex items-center gap-1.5 text-xs font-semibold transition-colors ${
                        isDark ? 'text-teal-400 hover:text-emerald-300' : 'text-teal-700 hover:text-teal-900'
                    }`}
                >
                    {block.action.label}
                    <ArrowRight className="h-3 w-3" />
                </button>
            )}
        </Card>
    )
}
