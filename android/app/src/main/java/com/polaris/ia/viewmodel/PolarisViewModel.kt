// Polaris IA — ViewModel
// Gestiona el estado de la IA y la comunicación con el servidor y Supabase Realtime

package com.polaris.ia.viewmodel

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.AnimationVector1D
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.polaris.ia.data.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlin.math.*
import kotlin.random.Random

// ─────────────────────────────────────────────
//  ESTADO DE UNA NEURONA CON ANIMACIONES
// ─────────────────────────────────────────────

class AnimatedNeuron(
    val neuron: Neuron,
    val scale: Animatable<Float, AnimationVector1D> = Animatable(0.3f),
    val glow: Animatable<Float, AnimationVector1D> = Animatable(0.2f)
)

// ─────────────────────────────────────────────
//  VIEWMODEL PRINCIPAL
// ─────────────────────────────────────────────

class PolarisViewModel : ViewModel() {

    // URL del servidor FastAPI en Hugging Face
    private val serverBaseUrl = "https://pdlc-polaris-ia.hf.space"
    private val metricsUrl   = "$serverBaseUrl/status"
    private val progressUrl  = "$serverBaseUrl/progress"

    // ── Estado observable ─────────────────────

    private val _animatedNeurons = MutableStateFlow<List<AnimatedNeuron>>(emptyList())
    val animatedNeurons: StateFlow<List<AnimatedNeuron>> = _animatedNeurons.asStateFlow()

    private val _connections = MutableStateFlow<List<Connection>>(emptyList())
    val connections: StateFlow<List<Connection>> = _connections.asStateFlow()

    private val _metrics = MutableStateFlow(LearningMetrics())
    val metrics: StateFlow<LearningMetrics> = _metrics.asStateFlow()

    private val _statusMessage = MutableStateFlow("Conectando con Polaris IA...")
    val statusMessage: StateFlow<String> = _statusMessage.asStateFlow()

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected.asStateFlow()

    private val _progress = MutableStateFlow(LearningProgress())
    val progress: StateFlow<LearningProgress> = _progress.asStateFlow()

    // ── Dimensiones del canvas (se actualizan desde la UI) ────
    var canvasWidth: Float = 1080f
    var canvasHeight: Float = 1920f

    init {
        startPolling()
    }

    // ─────────────────────────────────────────
    //  POLLING A LA API (cada 5 segundos)
    //  Fallback simple que no requiere WebSocket
    // ─────────────────────────────────────────

    private fun startPolling() {
        viewModelScope.launch {
            while (true) {
                try {
                    fetchMetrics()
                    fetchProgress()
                    _isConnected.value = true
                } catch (e: Exception) {
                    _isConnected.value = false
                    _statusMessage.value = "Reconectando..."
                }
                delay(if (_progress.value.active) 1000 else 5000)
            }
        }
    }

    private suspend fun fetchProgress() {
        val result = withContext(Dispatchers.IO) {
            try {
                val url = java.net.URL(progressUrl)
                val conn = url.openConnection() as java.net.HttpURLConnection
                conn.connectTimeout = 3000
                conn.readTimeout = 3000
                val response = conn.inputStream.bufferedReader().readText()
                conn.disconnect()
                response
            } catch (e: Exception) {
                null
            }
        }
        result?.let { json ->
            parseAndUpdateProgress(json)
        }
    }

    private suspend fun fetchMetrics() {
        // Usar HttpURLConnection simple (sin dependencias extra)
        val result = withContext(Dispatchers.IO) {
            try {
                val url = java.net.URL(metricsUrl)
                val conn = url.openConnection() as java.net.HttpURLConnection
                conn.connectTimeout = 5000
                conn.readTimeout = 5000
                val response = conn.inputStream.bufferedReader().readText()
                conn.disconnect()
                response
            } catch (e: Exception) {
                null
            }
        }

        result?.let { json ->
            parseAndUpdateMetrics(json)
        }
    }

    // ─────────────────────────────────────────
    //  PARSEO DE RESPUESTA JSON (manual, sin Gson)
    // ─────────────────────────────────────────

    private fun parseAndUpdateMetrics(json: String) {
        try {
            // Fallback: intentar encontrar 'neurons' o 'neuronas' o la versión anidada
            val neurons = extractInt(json, "neurons") 
                ?: extractInt(json, "neuronas")
                ?: 0
            
            val connections = extractInt(json, "connections") ?: 0
            val loss = extractFloat(json, "loss") ?: extractFloat(json, "pérdida_actual") ?: 0f
            val texts = extractInt(json, "texts_learned") ?: extractInt(json, "textos_totales") ?: 0
            val growth = extractInt(json, "growth_events") ?: extractInt(json, "eventos_de_crecimiento") ?: 0
            val topic = extractString(json, "last_topic") ?: extractString(json, "tema") ?: "Sincronizando..."

            val newMetrics = LearningMetrics(
                neurons = neurons,
                connections = connections,
                currentLoss = loss,
                textsLearned = texts,
                growthEvents = growth,
                lastTopic = topic,
                lastUpdate = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
                    .format(java.util.Date())
            )

            val currentCount = _animatedNeurons.value.size
            if (neurons != currentCount && neurons > 0) {
                updateNeuronVisualization(neurons, connections)
            }

            _metrics.value = newMetrics
            _statusMessage.value = "🧠 Polaris IA activa — ${neurons} neuronas"

        } catch (e: Exception) {
            _statusMessage.value = "Error de sincronización"
        }
    }

    private fun parseAndUpdateProgress(json: String) {
        try {
            val active = json.contains("\"active\":true")
            val phase = extractString(json, "phase") ?: "idle"
            val percent = extractInt(json, "percent") ?: 0
            val topic = extractString(json, "topic") ?: ""
            val step = extractInt(json, "step") ?: 0
            val total = extractInt(json, "total_steps") ?: 0
            val gained = extractInt(json, "neurons_gained") ?: 0

            _progress.value = LearningProgress(
                active = active,
                phase = phase,
                percent = percent,
                topic = topic,
                step = step,
                totalSteps = total,
                neuronsGained = gained
            )
        } catch (e: Exception) {}
    }

    // ─────────────────────────────────────────
    //  ACTUALIZAR VISUALIZACIÓN DE LA RED
    // ─────────────────────────────────────────

    private fun updateNeuronVisualization(targetNeurons: Int, targetConnections: Int) {
        viewModelScope.launch {
            val current = _animatedNeurons.value.toMutableList()
            val currentCount = current.size

            if (targetNeurons > currentCount) {
                // Añadir nuevas neuronas con animación de pulso
                val newNeurons = mutableListOf<AnimatedNeuron>()

                repeat(targetNeurons - currentCount) { i ->
                    val idx = currentCount + i
                    val position = calculateNeuronPosition(idx, targetNeurons)

                    val animNeuron = AnimatedNeuron(
                        neuron = Neuron(
                            id = "N$idx",
                            x = position.first,
                            y = position.second,
                            layer = idx / maxOf(1, targetNeurons / 4),
                            status = NeuronStatus.NEW
                        )
                    )
                    newNeurons.add(animNeuron)
                }

                current.addAll(newNeurons)
                _animatedNeurons.value = current.toList()

                // Animar aparición de las nuevas neuronas
                newNeurons.forEach { animNeuron ->
                    launch {
                        // Pulso de entrada: crece rápido y luego estabiliza
                        animNeuron.scale.animateTo(1.8f,
                            androidx.compose.animation.core.tween(300))
                        animNeuron.scale.animateTo(1.0f,
                            androidx.compose.animation.core.tween(200))
                        animNeuron.glow.animateTo(0.9f,
                            androidx.compose.animation.core.tween(200))
                        animNeuron.glow.animateTo(0.4f,
                            androidx.compose.animation.core.tween(500))
                    }
                }
            }

            // Actualizar conexiones
            val newConnections = generateConnections(
                _animatedNeurons.value.map { it.neuron },
                targetConnections
            )
            _connections.value = newConnections

            // Activar algunas neuronas aleatoriamente para efecto visual
            activateRandomNeurons()
        }
    }

    private fun calculateNeuronPosition(index: Int, total: Int): Pair<Float, Float> {
        // Layout en espiral para que se vea dinámico y orgánico
        val angle = index * 137.5f * (Math.PI / 180f)  // Ángulo áureo
        val radius = 60f + (index * 18f)
        val centerX = canvasWidth / 2f
        val centerY = canvasHeight * 0.45f

        val x = (centerX + radius * cos(angle)).toFloat()
            .coerceIn(40f, canvasWidth - 40f)
        val y = (centerY + radius * sin(angle)).toFloat()
            .coerceIn(40f, canvasHeight * 0.85f)

        return Pair(x, y)
    }

    private fun generateConnections(neurons: List<Neuron>, maxConnections: Int): List<Connection> {
        if (neurons.size < 2) return emptyList()
        val connections = mutableListOf<Connection>()
        val limit = minOf(maxConnections / 10, neurons.size * 3, 500)

        repeat(limit) {
            val fromIdx = Random.nextInt(neurons.size)
            val toIdx = Random.nextInt(neurons.size)
            if (fromIdx != toIdx) {
                connections.add(
                    Connection(
                        fromId = neurons[fromIdx].id,
                        toId = neurons[toIdx].id,
                        strength = Random.nextFloat() * 0.8f + 0.2f
                    )
                )
            }
        }
        return connections
    }

    private fun activateRandomNeurons() {
        viewModelScope.launch {
            val neurons = _animatedNeurons.value
            if (neurons.isEmpty()) return@launch

            // Activar 3 neuronas aleatorias con un pulso
            repeat(3) {
                val idx = Random.nextInt(neurons.size)
                launch {
                    neurons[idx].glow.animateTo(1.0f,
                        androidx.compose.animation.core.tween(200))
                    delay(300)
                    neurons[idx].glow.animateTo(0.3f,
                        androidx.compose.animation.core.tween(600))
                }
            }
        }
    }

    // ─────────────────────────────────────────
    //  PARSEO JSON MANUAL (sin dependencias)
    // ─────────────────────────────────────────

    private fun extractInt(json: String, key: String): Int? {
        val regex = Regex(""""$key"\s*:\s*(\d+)""")
        return regex.find(json)?.groupValues?.get(1)?.toIntOrNull()
    }

    private fun extractFloat(json: String, key: String): Float? {
        val regex = Regex(""""$key"\s*:\s*([\d.]+)""")
        return regex.find(json)?.groupValues?.get(1)?.toFloatOrNull()
    }

    private fun extractString(json: String, key: String): String? {
        val regex = Regex(""""$key"\s*:\s*"([^"]*?)"""")
        return regex.find(json)?.groupValues?.get(1)
    }
}
