package app.io

import app.model.Lesson
import app.model.Vocabulary
import app.util.JsonTools
import com.fasterxml.jackson.databind.ObjectWriter
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import kotlin.io.path.createDirectories

class Writer {
    private val mapper = JsonTools.mapper
    private val writer: ObjectWriter = mapper.writerWithDefaultPrettyPrinter()

    fun writeLessons(path: Path, lessons: List<Lesson>) {
        ensureParent(path)
        writer.writeValue(path.toFile(), lessons)
    }

    fun writeVocabulary(path: Path, vocab: List<Vocabulary>) {
        ensureParent(path)
        writer.writeValue(path.toFile(), vocab)
    }

    fun writeText(path: Path, text: String) {
        ensureParent(path)
        Files.writeString(path, text)
    }

    private fun ensureParent(path: Path) {
        val parent = path.parent
        if (parent != null && !Files.exists(parent)) {
            parent.createDirectories()
        }
    }

    companion object {
        fun canonicalLessonsPath(): Path = Paths.get("build/canonical/lessons.mmspanish.json")
        fun canonicalVocabularyPath(): Path = Paths.get("build/canonical/vocabulary.mmspanish.json")
        fun auditPath(): Path = Paths.get("build/reports/audit.md")
        fun rejectsDir(): Path = Paths.get("build/rejects")
    }
}
