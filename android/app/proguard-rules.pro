# ProGuard rules para Polaris IA
# Mantiene las clases de Compose y Kotlin intactas

-keep class androidx.compose.** { *; }
-keep class kotlin.** { *; }
-keep class kotlinx.coroutines.** { *; }
-keep class com.polaris.ia.** { *; }

# No eliminar los Composables
-keepclassmembers class * {
    @androidx.compose.runtime.Composable *;
}

# Suprimir advertencias de clases internas de Kotlin
-dontwarn kotlin.Unit
-dontwarn kotlin.reflect.**
