import com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar

buildscript {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
    dependencies {
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.24")
        classpath("com.github.johnrengelman:shadow:8.1.1")
    }
}

apply(plugin = "org.jetbrains.kotlin.jvm")
apply(plugin = "com.github.johnrengelman.shadow")
apply(plugin = "application")

repositories {
    mavenCentral()
}

dependencies {
    implementation("com.fasterxml.jackson.core:jackson-databind:2.17.+")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin:2.17.+")
    implementation("com.fasterxml.jackson.dataformat:jackson-dataformat-yaml:2.17.+")
    implementation("org.everit.json:org.everit.json.schema:1.14.2")
    implementation("info.picocli:picocli:4.7.6")
    implementation("org.slf4j:slf4j-simple:2.0.+")
    implementation("com.github.slugify:slugify:3.0.7")
    implementation("commons-codec:commons-codec:1.16.1")
    implementation(kotlin("stdlib"))
}

application {
    mainClass.set("app.Main")
}

kotlin {
    jvmToolchain(17)
}

tasks.withType<ShadowJar> {
    archiveFileName.set("codex-rebuilder-all.jar")
    manifest {
        attributes(mapOf("Main-Class" to "app.Main"))
    }
}

tasks.withType<Jar> {
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
}
