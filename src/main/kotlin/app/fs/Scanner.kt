package app.fs

import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.nio.file.attribute.BasicFileAttributes
import kotlin.io.path.isRegularFile

class Scanner {
    data class ScannedFile(val path: Path, val mtime: Long, val content: String)

    fun scan(root: Path = Paths.get("content")): List<ScannedFile> {
        if (!Files.exists(root)) return emptyList()
        val results = mutableListOf<ScannedFile>()
        Files.walk(root).use { stream ->
            stream.filter { it.isRegularFile() }
                .filter { Files.size(it) > 0 }
                .sorted()
                .forEach { path ->
                    val attrs = Files.readAttributes(path, BasicFileAttributes::class.java)
                    val content = Files.readString(path)
                    results.add(ScannedFile(path, attrs.lastModifiedTime().toMillis(), content))
                }
        }
        return results
    }
}
