// Top-level build file. Plugin versions live here, once.
// Tested pairing: AGP 8.7.3 + Gradle 8.9 + Kotlin 2.0.21 (Compose compiler is a Kotlin plugin since 2.0).
plugins {
    id("com.android.application") version "8.7.3" apply false
    id("org.jetbrains.kotlin.android") version "2.0.21" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false
}
