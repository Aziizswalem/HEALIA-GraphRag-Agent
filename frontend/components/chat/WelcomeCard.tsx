'use client'

import PromptCards from './PromptCards'

type Props = {
    onPrompt: (text: string) => void
    bgStyle?: 'clinical-light' | 'neon-matrix'
}

export default function WelcomeCard({ onPrompt, bgStyle = 'clinical-light' }: Props) {
    const isLight = bgStyle === 'clinical-light'

    return (
        <div className={`w-full max-w-2xl rounded-3xl border p-5 md:p-6 backdrop-blur-md transition-colors duration-700 ${bgStyle === 'clinical-light'
                ? 'border-white/80 bg-white/35 text-gray-800'
                : 'border-healia-green/10 bg-[#020508]/35 text-emerald-100'
            }`}>
            <div className="flex items-center gap-3.5 mb-5">
                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl p-1 shadow-sm border ${isLight ? 'bg-healia-teal/10 border-healia-teal/30' : 'bg-white/5 border-white/10'
                    }`}>
                    <img src="/healio.jpg" className="h-full w-full object-cover rounded-lg" alt="Healio.jpg Logo" />
                </div>
                <div>
                    <h2 className="text-lg font-bold bg-gradient-to-r from-healia-teal to-healia-dark bg-clip-text text-transparent leading-none">Healia Chatbot</h2>
                    <p className={`mt-1 text-xs leading-tight ${isLight ? 'text-gray-500' : 'text-gray-400'}`}>
                        Bienvenue sur votre espace d'analyse médicale propulsé par graphe.
                    </p>
                </div>
            </div>

            <h3 className={`text-[10px] font-bold uppercase tracking-wider mb-2.5 ${isLight ? 'text-gray-450' : 'text-healia-green/60'}`}>
                Explorations suggérées de la base Neo4j
            </h3>
            <PromptCards onPrompt={onPrompt} bgStyle={bgStyle} />
        </div>
    )
}