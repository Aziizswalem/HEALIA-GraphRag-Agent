export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    attachedFile?: string;
    /** Thinking time in seconds for the assistant response */
    thinkingTime?: number;
    /** Cypher representation of the query executed in Neo4j graphdb */
    cypherQuery?: string;
    /** Active nodes or subgraph elements returned by the graph search */
    graphDataHighlight?: {
        nodes: string[];
        edges: string[];
    };
    /** GenUI blocks for rich interactive content */
    genuiBlocks?: GenuiBlock[];
    /** Identifiant de trace Langfuse pour observabilité */
    traceId?: string;
    /** Plan d'exécution Neo4j (EXPLAIN / PROFILE) */
    executionPlan?: string;
    /** Latence de la requête en millisecondes */
    latencyMs?: number;
    /** Afficher le fil d'Ariane de raisonnement (Reasoning Stepper) */
    hasStepper?: boolean;
    /** Étape courante du fil d'Ariane (0 à 4 en live, 5 quand terminé) */
    currentStep?: number;
    /** Indique si le raisonnement agentique est en cours d'exécution */
    isLive?: boolean;
    /** Commande directe déterministe shortcut (ex: \adherent 1426) */
    isShortcut?: boolean;
    /** Étapes personnalisées du stepper */
    stepperSteps?: any[];
    /** Durée totale du stepper (ex: '8.0s' ou '25ms') */
    stepperTotal?: string;
}

export type GenuiBlockType = 'chart' | 'card' | 'table' | 'form' | 'button' | 'canvas' | 'graph';

export interface ChartBlock {
    type: 'chart';
    chartType: 'bar' | 'pie' | 'line' | 'scatter';
    title?: string;
    data: Record<string, any>[];
    xKey?: string;
    yKey?: string;
    valueUnit?: 'currency' | 'number' | 'count';
}

export interface CardBlock {
    type: 'card';
    title: string;
    description?: string;
    image?: string;
    badge?: string;
    action?: { label: string; url?: string };
    nom?: string;
    contrat?: string;
    statut?: string;
    plafond_annuel?: string;
    consommation?: string;
}

export interface TableBlock {
    type: 'table';
    title?: string;
    columns: string[];
    rows: Record<string, any>[];
}

export interface FormField {
    name: string;
    label: string;
    type: 'text' | 'number' | 'select' | 'slider';
    options?: string[];
}

export interface FormBlock {
    type: 'form';
    title?: string;
    fields: FormField[];
}

export interface ButtonBlock {
    type: 'button';
    label: string;
    action: string;
}

export interface CanvasBlock {
    type: 'canvas';
    title?: string;
    children: GenuiBlock[];
}

export interface GraphNodeData {
    id: string;
    label: string;
    type: string;
    badge?: string;
    properties?: Record<string, any>;
}

export interface GraphEdgeData {
    source: string;
    target: string;
    label: string;
}

export interface GraphBlock {
    type: 'graph';
    title?: string;
    description?: string;
    nodes: GraphNodeData[];
    edges: GraphEdgeData[];
}

export type GenuiBlock = ChartBlock | CardBlock | TableBlock | FormBlock | ButtonBlock | CanvasBlock | GraphBlock;

export interface SessionItem {
    id: string;
    title: string;
    time: string;
    messages: Message[];
}

export interface GraphNode {
    id: string;
    label: string;
    type: 'Patient' | 'Claim' | 'Provider' | 'Diagnosis' | 'Policy';
    properties: Record<string, any>;
    x?: number;
    y?: number;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    label: string;
    properties?: Record<string, any>;
}