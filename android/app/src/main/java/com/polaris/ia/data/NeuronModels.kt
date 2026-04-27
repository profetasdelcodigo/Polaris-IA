// Polaris IA — Neuron Data Models
// Data classes para representar la red neuronal en la UI de Android

package com.polaris.ia.data

import java.util.UUID

// ─────────────────────────────────────────────
//  ESTADO DE UNA NEURONA
// ─────────────────────────────────────────────

enum class NeuronStatus {
    IDLE,       // Azul — inactiva, reposo
    LEARNING,   // Verde — aprendiendo algo nuevo
    ACTIVE,     // Blanco brillante — muy activa
    NEW         // Cyan pulsante — recién creada
}

data class Neuron(
    val id: String = UUID.randomUUID().toString(),
    val x: Float,
    val y: Float,
    val layer: Int = 0,            // Capa a la que pertenece
    val activation: Float = 0f,   // 0.0 = inactiva, 1.0 = máxima activación
    val status: NeuronStatus = NeuronStatus.IDLE
)

// ─────────────────────────────────────────────
//  CONEXIÓN ENTRE NEURONAS
// ─────────────────────────────────────────────

data class Connection(
    val fromId: String,
    val toId: String,
    val strength: Float = 0.5f    // Fuerza de la conexión (grosor de la línea)
)

// ─────────────────────────────────────────────
//  ESTADO COMPLETO DE LA RED NEURONAL
//  Mapeado desde la API REST del servidor
// ─────────────────────────────────────────────

data class NetworkState(
    val neurons: List<Neuron> = emptyList(),
    val connections: List<Connection> = emptyList(),
    val totalNeurons: Int = 0,
    val totalParams: Int = 0,
    val layers: List<Int> = emptyList()
)

// ─────────────────────────────────────────────
//  MÉTRICAS DE APRENDIZAJE
//  Para el panel derecho del dashboard
// ─────────────────────────────────────────────

data class LearningMetrics(
    val neurons: Int = 0,
    val connections: Int = 0,
    val currentLoss: Float = 0f,
    val textsLearned: Int = 0,
    val growthEvents: Int = 0,
    val lastTopic: String = "Iniciando...",
    val lastUpdate: String = "",
    val semanticMemories: Int = 0,
    val learningEvents: Int = 0,
    val replayBufferSize: Int = 0
)

// ─────────────────────────────────────────────
//  EVENTO DE CRECIMIENTO
//  Cuando la red añade nuevas neuronas
// ─────────────────────────────────────────────

data class GrowthEvent(
    val timestamp: String,
    val neuronsAdded: Int,
    val layer: Int,
    val totalNeuronsAfter: Int
)
