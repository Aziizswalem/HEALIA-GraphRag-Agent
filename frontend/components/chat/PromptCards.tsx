'use client'

import { Shield, Activity, Database } from 'lucide-react'

type Props = {
    onPrompt: (text: string) => void
    bgStyle?: 'clinical-light' | 'neon-matrix'
}

export default function PromptCards({ onPrompt, bgStyle = 'clinical-light' }: Props) {
    const isDark = bgStyle !== 'clinical-light'

    const SUGGESTIONS = [
        {
            title: "Audit Chronique & Suivi",
            desc: "Détecter les assurés chroniques avec des bulletins de soins éffectués sur 3 mois.",
            prompt: "Quels assurés ont des bulletins de soins après leur date de radiation ?",
            icon: <Database className="h-4 w-4 text-healia-teal" />
        },
        {
            title: "Vue Générale",
            desc: "Accès instantané déterministe aux détails des prestations et historique BS.",
            prompt: "\\adherent 1426",
            icon: <Shield className="h-4 w-4 text-healia-green" />
        },
        {
            title: "Polices & Franchises",
            desc: "Résumer les allocations de franchise pour les membres couverts par Healia.",
            prompt: "Résumer les détails des prestations, quotes-parts et franchises pour les plans Healia PPO",
            icon: <Activity className="h-4 w-4 text-healia-teal" />
        }
    ]

    return (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
            {SUGGESTIONS.map((item, idx) => (
                <div
                    key={idx}
                    onClick={() => onPrompt(item.prompt)}
                    className={`group cursor-pointer rounded-2xl border p-4 text-left transition-all hover:scale-[1.01] hover:shadow-md ${isDark
                        ? 'bg-black/35 border-white/5 hover:border-healia-green/30 text-emerald-100 hover:bg-black/55'
                        : 'bg-white/80 border-slate-200/55 hover:border-healia-teal/50 text-slate-700 hover:bg-white'
                        }`}
                >
                    <div className={`mb-2 w-fit p-1.5 rounded-lg border ${isDark ? 'bg-white/5 border-white/10' : 'bg-slate-50 border-slate-100'
                        }`}>
                        {item.icon}
                    </div>
                    <h4 className={`text-xs font-bold transition-colors ${isDark ? 'group-hover:text-healia-green' : 'group-hover:text-healia-teal'
                        }`}>{item.title}</h4>
                    <p className={`mt-1 text-[11px] leading-snug transition-colors ${isDark ? 'text-gray-400/90 group-hover:text-gray-300' : 'text-gray-500 group-hover:text-gray-600'
                        }`}>{item.desc}</p>
                </div>
            ))}
        </div>
    )
}