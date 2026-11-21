plugins {
    kotlin("jvm") version "2.0.21"
    `maven-publish`
}

group = "dev.fluidian"
version = "1.2.0"

repositories {
    mavenCentral()
}

kotlin {
    jvmToolchain(11)
}

sourceSets {
    create("examples") {
        kotlin.srcDir("src/examples/kotlin")
        compileClasspath += sourceSets["main"].output
        runtimeClasspath += sourceSets["main"].output
    }
}
