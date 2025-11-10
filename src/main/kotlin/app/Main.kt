package app

import app.audit.Audit
import app.conflicts.ConflictResolver
import app.fs.Scanner
import app.io.Writer
import app.merge.DeepMerge
import app.merge.MergeContext
import app.model.Lesson
import app.model.Vocabulary
import app.normalize.Normalizer
import app.util.JsonTools
import app.validate.Validator
import com.fasterxml.jackson.databind.node.ArrayNode
import com.fasterxml.jackson.databind.node.ObjectNode
import info.picocli.CommandLine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.runBlocking
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.time.Duration
import java.time.Instant
import java.util.Comparator
import java.util.concurrent.Callable

@CommandLine.Command(name = "codex-rebuilder", mixinStandardHelpOptions = true)
class Main : Callable<Int> {
    @CommandLine.Option(
        names = ["--write"],
        description = ["Write canonical outputs (default: true)"],
        defaultValue = "true",
        negatable = true
    )
    var write: Boolean = true

    @CommandLine.Option(names = ["--check"], description = ["Run pipeline without writing"], defaultValue = "false")
    var check: Boolean = false

    @CommandLine.Option(names = ["--strict"], description = ["Fail on invalid or UNSET"], defaultValue = "false")
    var strict: Boolean = false

    override fun call(): Int = runBlocking {
        val start = Instant.now()
        val normalizer = Normalizer()
        val conflictResolver = ConflictResolver(normalizer)
        val scanner = Scanner()
        val writer = Writer()
        val validator = Validator()
        val audit = Audit()

        val scanned = scanner.scan()
        val fileMap = scanned.associateBy { it.path }.toSortedMap(compareBy { it.toString() })

        val asyncResults = fileMap.values.map { file ->
            async(Dispatchers.Default) {
                processFile(file, normalizer, conflictResolver)
            }
        }
        val results = asyncResults.awaitAll()

        val lessonMap = mutableMapOf<String, Accumulator>()
        val vocabMap = mutableMapOf<String, Accumulator>()
        val rejects = mutableListOf<RejectRecord>()
        var conflictCount = 0
        var parsedFragments = 0
        var duplicateClusters = 0

        results.zip(fileMap.values).sortedBy { it.second.path.toString() }.forEach { (result, file) ->
            conflictCount += result.conflicts
            parsedFragments += result.parsedFragments
            rejects += result.rejects
            result.lessons.forEach { (node, mtime) ->
                val key = lessonKey(node)
                val existing = lessonMap[key]
                if (existing == null) {
                    lessonMap[key] = Accumulator(node, mtime)
                } else {
                    val merged = DeepMerge.merge(existing.node, node, MergeContext(existing.mtime, mtime)) as ObjectNode
                    merged.set<ArrayNode>("source_files", JsonTools.mapper.valueToTree(DeepMerge.unionSourceLists(
                        JsonTools.mapper.convertValue(existing.node.get("source_files"), List::class.java) as List<String>,
                        JsonTools.mapper.convertValue(node.get("source_files"), List::class.java) as List<String>
                    )))
                    existing.node = merged
                    existing.mtime = maxOf(existing.mtime, mtime)
                    duplicateClusters += 1
                }
            }
            result.vocabulary.forEach { (node, mtime) ->
                val key = vocabKey(node)
                val existing = vocabMap[key]
                if (existing == null) {
                    vocabMap[key] = Accumulator(node, mtime)
                } else {
                    val merged = DeepMerge.merge(existing.node, node, MergeContext(existing.mtime, mtime)) as ObjectNode
                    merged.set<ArrayNode>("source_files", JsonTools.mapper.valueToTree(DeepMerge.unionSourceLists(
                        JsonTools.mapper.convertValue(existing.node.get("source_files"), List::class.java) as List<String>,
                        JsonTools.mapper.convertValue(node.get("source_files"), List::class.java) as List<String>
                    )))
                    existing.node = merged
                    existing.mtime = maxOf(existing.mtime, mtime)
                    duplicateClusters += 1
                }
            }
        }

        val lessonModels = lessonMap.values.map { JsonTools.mapper.treeToValue(it.node, Lesson::class.java) }
            .sortedBy { it.sortKey() }
        val vocabModels = vocabMap.values.map { JsonTools.mapper.treeToValue(it.node, Vocabulary::class.java) }
            .sortedBy { it.sortKey() }

        val lessonValidation = validator.validateLessons(lessonModels)
        val vocabValidation = validator.validateVocabulary(vocabModels)

        lessonValidation.invalid.forEach { rejects.add(RejectRecord("lesson", it.item.id, it.reason, JsonTools.mapper.writeValueAsString(it.item))) }
        vocabValidation.invalid.forEach { rejects.add(RejectRecord("vocabulary", it.item.id, it.reason, JsonTools.mapper.writeValueAsString(it.item))) }

        val finalLessons = lessonValidation.valid
        val finalVocab = vocabValidation.valid
        val unsetIds = (finalLessons.filter { it.level == "UNSET" }.map { it.id } +
                finalVocab.filter { it.level == "UNSET" }.map { it.id })

        val duration = Duration.between(start, Instant.now())

        val summary = audit.render(
            Audit.Summary(
                filesScanned = scanned.size,
                conflictsHealed = conflictCount,
                parsedFragments = parsedFragments,
                lessons = finalLessons.size,
                vocabulary = finalVocab.size,
                duplicateClusters = duplicateClusters,
                unsetLevelIds = unsetIds,
                rejects = rejects.size,
                rejectDetails = rejects.map { "${it.category}:${it.id} -> ${it.reason}" },
                duration = duration
            )
        )

        println(summary)

        val shouldWrite = !check && write
        if (shouldWrite) {
            writeOutputs(writer, finalLessons, finalVocab, summary, rejects)
            performIdempotencyCheck(writer)
        }

        if (strict && (rejects.isNotEmpty() || unsetIds.isNotEmpty())) {
            return@runBlocking 1
        }
        0
    }

    private fun performIdempotencyCheck(writer: Writer) {
        val lessonsPath = Writer.canonicalLessonsPath()
        val vocabPath = Writer.canonicalVocabularyPath()
        val firstHash = hashFile(lessonsPath) + hashFile(vocabPath)
        val lessons = JsonTools.mapper.readValue(Files.readString(lessonsPath), Array<Lesson>::class.java).toList()
        val vocab = JsonTools.mapper.readValue(Files.readString(vocabPath), Array<Vocabulary>::class.java).toList()
        writer.writeLessons(lessonsPath, lessons)
        writer.writeVocabulary(vocabPath, vocab)
        val secondHash = hashFile(lessonsPath) + hashFile(vocabPath)
        if (firstHash != secondHash) {
            error("Idempotency check failed: hashes diverged")
        }
    }

    private fun hashFile(path: Path): String {
        if (!Files.exists(path)) return ""
        val digest = MessageDigest.getInstance("SHA-256")
        val bytes = Files.readAllBytes(path)
        val hash = digest.digest(bytes)
        return hash.joinToString("") { "%02x".format(it) }
    }

    private fun writeOutputs(
        writer: Writer,
        lessons: List<Lesson>,
        vocab: List<Vocabulary>,
        auditText: String,
        rejects: List<RejectRecord>
    ) {
        writer.writeLessons(Writer.canonicalLessonsPath(), lessons)
        writer.writeVocabulary(Writer.canonicalVocabularyPath(), vocab)
        writer.writeText(Writer.auditPath(), auditText)
        writeRejects(rejects)
    }

    private fun writeRejects(rejects: List<RejectRecord>) {
        val dir = Writer.rejectsDir()
        if (Files.exists(dir)) {
            Files.walk(dir).use { stream ->
                stream.sorted(Comparator.reverseOrder())
                    .forEach { if (it != dir) Files.deleteIfExists(it) }
            }
        }
        Files.createDirectories(dir)
        rejects.sortedWith(compareBy({ it.category }, { it.id })).forEachIndexed { index, reject ->
            val name = "%03d_${reject.category}_${reject.id.ifBlank { "unknown" }}.txt".format(index)
            val path = dir.resolve(name)
            val body = buildString {
                appendLine("Reason: ${reject.reason}")
                appendLine("Fragment:")
                appendLine(reject.fragment)
            }
            Files.writeString(path, body)
        }
    }

    private fun lessonKey(node: ObjectNode): String {
        val title = node.path("title").asText()
        val unit = node.path("unit").asInt()
        val lesson = node.path("lesson_number").asInt()
        return listOf(title.lowercase(), unit.toString(), lesson.toString()).joinToString("|")
    }

    private fun vocabKey(node: ObjectNode): String {
        val spanish = node.path("spanish").asText().lowercase()
        val pos = node.path("pos").asText().lowercase()
        val genderNode = node.get("gender")
        val gender = if (genderNode != null && !genderNode.isNull) genderNode.asText().lowercase() else ""
        return listOf(spanish, pos, gender).joinToString("|")
    }

    private fun processFile(
        file: Scanner.ScannedFile,
        normalizer: Normalizer,
        conflictResolver: ConflictResolver
    ): FileResult {
        val level = normalizer.inferLevelFromPath(file.path)
        val conflict = conflictResolver.healConflicts(file.content, file.path, file.mtime)
        val context = Normalizer.FragmentContext(file.path, file.mtime, level)
        val normalized = normalizer.normalize(conflict.healedText, context)
        val rejects = mutableListOf<RejectRecord>()
        conflict.rejects.forEach { rejects.add(RejectRecord("conflict", file.path.fileName.toString(), it.reason, it.fragment)) }
        normalized.rejects.forEach { rejects.add(RejectRecord("parse", file.path.fileName.toString(), it.reason, it.fragment)) }
        return FileResult(
            lessons = normalized.lessons,
            vocabulary = normalized.vocabulary,
            conflicts = conflict.healedCount,
            parsedFragments = normalized.parsedFragments,
            rejects = rejects
        )
    }

    data class Accumulator(var node: ObjectNode, var mtime: Long)

    data class RejectRecord(val category: String, val id: String, val reason: String, val fragment: String)

    data class FileResult(
        val lessons: List<Pair<ObjectNode, Long>>,
        val vocabulary: List<Pair<ObjectNode, Long>>,
        val conflicts: Int,
        val parsedFragments: Int,
        val rejects: List<RejectRecord>
    )
}

fun main(vararg args: String): Int = CommandLine(Main()).execute(*args)
