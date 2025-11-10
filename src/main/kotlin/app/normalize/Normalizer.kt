package app.normalize

import app.model.LessonStep
import app.parse.Extractor
import app.util.Ids
import app.util.JsonTools
import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.node.ArrayNode
import com.fasterxml.jackson.databind.node.ObjectNode
import java.nio.file.Path
import java.util.Locale

class Normalizer {
    private val mapper = JsonTools.mapper
    private val extractor = Extractor()

    data class FragmentContext(val path: Path, val mtime: Long, val inferredLevel: String)

    data class NormalizedResult(
        val lessons: List<Pair<ObjectNode, Long>>,
        val vocabulary: List<Pair<ObjectNode, Long>>,
        val rejects: List<Reject>,
        val parsedFragments: Int
    )

    data class Reject(val source: Path, val reason: String, val fragment: String)

    fun normalize(text: String, context: FragmentContext): NormalizedResult {
        val fragments = extractor.extract(text)
        val lessonNodes = mutableListOf<Pair<ObjectNode, Long>>()
        val vocabNodes = mutableListOf<Pair<ObjectNode, Long>>()
        val rejects = mutableListOf<Reject>()
        var parsedCount = 0
        for (fragment in fragments) {
            val nodes = tryParse(fragment)
            if (nodes.isEmpty()) {
                rejects.add(Reject(context.path, "Unable to parse JSON fragment", fragment.trim()))
                continue
            }
            parsedCount += nodes.size
            for (node in nodes) {
                when {
                    node.isArray -> {
                        node.forEach { child ->
                            processNode(child, context, lessonNodes, vocabNodes, rejects)
                        }
                    }
                    node.isObject -> processNode(node, context, lessonNodes, vocabNodes, rejects)
                    else -> rejects.add(Reject(context.path, "Unsupported JSON node", node.toString()))
                }
            }
        }
        return NormalizedResult(lessonNodes, vocabNodes, rejects, parsedCount)
    }

    fun tryParse(fragment: String): List<JsonNode> = tryParseInternal(fragment)

    private fun tryParseInternal(fragment: String): List<JsonNode> {
        val attempts = listOf(::strictParse, ::repairSingleQuotes, ::repairTrailingCommas, ::balanceBrackets)
        var current = fragment
        attempts.forEachIndexed { index, parser ->
            val result = parser(current)
            if (result != null) {
                return result
            }
            if (index < attempts.lastIndex) {
                current = quickFix(current, index)
            }
        }
        return emptyList()
    }

    private fun strictParse(text: String): List<JsonNode>? = runCatching {
        listOf(mapper.readTree(text))
    }.getOrNull()

    private fun repairSingleQuotes(text: String): List<JsonNode>? = runCatching {
        listOf(mapper.readTree(text.replace("'", "\"")))
    }.getOrNull()

    private fun repairTrailingCommas(text: String): List<JsonNode>? = runCatching {
        val noTrailing = text.replace(",\\s*[}\]]".toRegex()) { match ->
            match.value.trim().last().toString()
        }
        listOf(mapper.readTree(noTrailing))
    }.getOrNull()

    private fun balanceBrackets(text: String): List<JsonNode>? = runCatching {
        val balanced = balance(text)
        listOf(mapper.readTree(balanced))
    }.getOrNull()

    private fun quickFix(input: String, attempt: Int): String {
        return when (attempt) {
            0 -> input.replace("([a-zA-Z0-9_]+)\s*:".toRegex()) { match ->
                val key = match.groupValues[1]
                "\"$key\":"
            }
            1 -> input
            2 -> balance(input)
            else -> input
        }
    }

    private fun balance(text: String): String {
        var openCurly = text.count { it == '{' }
        var closeCurly = text.count { it == '}' }
        var openBracket = text.count { it == '[' }
        var closeBracket = text.count { it == ']' }
        val builder = StringBuilder(text.trim())
        while (openCurly > closeCurly) {
            builder.append('}')
            closeCurly += 1
        }
        while (openBracket > closeBracket) {
            builder.append(']')
            closeBracket += 1
        }
        return builder.toString()
    }

    private fun processNode(
        node: JsonNode,
        context: FragmentContext,
        lessons: MutableList<Pair<ObjectNode, Long>>,
        vocab: MutableList<Pair<ObjectNode, Long>>,
        rejects: MutableList<Reject>
    ) {
        when {
            node.isObject -> classifyObject(node as ObjectNode, context, lessons, vocab, rejects)
            node.isArray -> node.forEach { child -> processNode(child, context, lessons, vocab, rejects) }
            else -> rejects.add(Reject(context.path, "Unrecognized structure", node.toString()))
        }
    }

    private fun classifyObject(
        node: ObjectNode,
        context: FragmentContext,
        lessons: MutableList<Pair<ObjectNode, Long>>,
        vocab: MutableList<Pair<ObjectNode, Long>>,
        rejects: MutableList<Reject>
    ) {
        val hasLessonFields = node.has("steps") || node.has("lesson_number") || node.has("unit")
        val hasVocabFields = node.has("spanish") || node.has("english_gloss") || node.has("definition")
        when {
            node.has("lessons") -> {
                val arr = node.get("lessons")
                if (arr is ArrayNode) arr.forEach { processNode(it, context, lessons, vocab, rejects) }
            }
            node.has("vocabulary") -> {
                val arr = node.get("vocabulary")
                if (arr is ArrayNode) arr.forEach { processNode(it, context, lessons, vocab, rejects) }
            }
            hasLessonFields && hasVocabFields -> {
                classifyLesson(node, context)?.let { lessons.add(it to context.mtime) }
                classifyVocabulary(node, context)?.let { vocab.add(it to context.mtime) }
            }
            hasLessonFields -> {
                val normalized = classifyLesson(node, context)
                if (normalized != null) {
                    lessons.add(normalized to context.mtime)
                } else {
                    rejects.add(Reject(context.path, "Incomplete lesson", node.toString()))
                }
            }
            hasVocabFields -> {
                val normalized = classifyVocabulary(node, context)
                if (normalized != null) {
                    vocab.add(normalized to context.mtime)
                } else {
                    rejects.add(Reject(context.path, "Incomplete vocabulary", node.toString()))
                }
            }
            else -> rejects.add(Reject(context.path, "Unknown object", node.toString()))
        }
    }

    private fun classifyLesson(node: ObjectNode, context: FragmentContext): ObjectNode? {
        val title = node.path("title").asText(null) ?: return null
        val nickname = node.path("nickname").asText().ifBlank { slugify(title) }
        val unitNode = node.get("unit")
        val lessonNode = node.get("lesson_number")
        val unit = unitNode?.asInt() ?: node.path("unit_number").asInt(-1)
        val lessonNumber = lessonNode?.asInt() ?: node.path("lessonNo").asInt(-1)
        if (unit < 0 || lessonNumber < 0) return null
        val level = normalizeLevel(node.path("level").asText(null), context.inferredLevel)
        val tags = collectStrings(node.get("tags"))
        val steps = buildSteps(node.get("steps"))
        val sourceFiles = ensureSource(node, context.path)
        val notes = node.path("notes").asText(null)
        val objectNode = mapper.createObjectNode()
        objectNode.put("id", Ids.lessonId(title, unit, lessonNumber))
        objectNode.put("title", title)
        objectNode.put("nickname", nickname)
        objectNode.put("level", level)
        objectNode.put("unit", unit)
        objectNode.put("lesson_number", lessonNumber)
        objectNode.set<ArrayNode>("tags", mapper.valueToTree(tags.sorted()))
        objectNode.set<ArrayNode>("steps", mapper.valueToTree(steps))
        notes?.let { objectNode.put("notes", it) }
        objectNode.set<ArrayNode>("source_files", mapper.valueToTree(sourceFiles))
        return objectNode
    }

    private fun classifyVocabulary(node: ObjectNode, context: FragmentContext): ObjectNode? {
        val spanish = node.path("spanish").asText(null) ?: node.path("term").asText(null) ?: return null
        val pos = node.path("pos").asText(null) ?: node.path("part_of_speech").asText(null) ?: return null
        val english = node.path("english_gloss").asText(null) ?: node.path("english").asText(null) ?: return null
        val definition = node.path("definition").asText(null) ?: node.path("explanation").asText(null) ?: return null
        val level = normalizeLevel(node.path("level").asText(null), context.inferredLevel)
        val origin = node.path("origin").takeIf { it.isTextual }?.asText()
        val story = node.path("story").takeIf { it.isTextual }?.asText()
        val gender = node.path("gender").takeIf { it.isTextual }?.asText()
        val examples = buildExamples(node.get("examples"))
        if (examples.isEmpty()) return null
        val tags = collectStrings(node.get("tags"))
        val notes = node.path("notes").asText(null)
        val sourceFiles = ensureSource(node, context.path)
        val objectNode = mapper.createObjectNode()
        objectNode.put("id", Ids.vocabId(spanish, pos, gender))
        objectNode.put("spanish", spanish)
        objectNode.put("pos", pos.lowercase(Locale.ENGLISH))
        gender?.let { objectNode.put("gender", it) } ?: objectNode.putNull("gender")
        objectNode.put("english_gloss", english)
        objectNode.put("definition", definition)
        origin?.let { objectNode.put("origin", it) } ?: objectNode.putNull("origin")
        story?.let { objectNode.put("story", it) } ?: objectNode.putNull("story")
        objectNode.set<ArrayNode>("examples", mapper.valueToTree(examples))
        objectNode.put("level", level)
        objectNode.set<ArrayNode>("tags", mapper.valueToTree(tags.sorted()))
        objectNode.set<ArrayNode>("source_files", mapper.valueToTree(sourceFiles))
        notes?.let { objectNode.put("notes", it) }
        return objectNode
    }

    private fun collectStrings(node: JsonNode?): List<String> {
        if (node == null || node.isNull) return emptyList()
        return when {
            node.isArray -> node.mapNotNull { it.asText(null) }.map { it.trim() }.filter { it.isNotBlank() }
            node.isTextual -> node.asText().split(",", "|").map { it.trim() }.filter { it.isNotBlank() }
            else -> emptyList()
        }
    }

    private fun ensureSource(node: ObjectNode, path: Path): List<String> {
        val existing = collectStrings(node.get("source_files"))
        val normalized = existing + path.toString()
        return normalized.toSet().toList().sorted()
    }

    private fun slugify(title: String): String = Ids.lessonId(title, 0, 0).substringAfterLast('_')

    private fun buildSteps(stepsNode: JsonNode?): List<LessonStep> {
        if (stepsNode == null || stepsNode.isNull) return emptyList()
        val result = mutableListOf<LessonStep>()
        if (stepsNode is ArrayNode) {
            for (step in stepsNode) {
                val phase = step.path("phase").asText(null) ?: continue
                val line = step.path("line").asText(null)
                val origin = step.path("origin").asText(null)
                val story = step.path("story").asText(null)
                val items = if (step.has("items")) collectStrings(step.get("items")) else emptyList()
                result.add(LessonStep(phase, line, origin, story, if (items.isEmpty()) null else items))
            }
        }
        return result
    }

    private fun buildExamples(examplesNode: JsonNode?): List<Map<String, String>> {
        if (examplesNode == null || examplesNode.isNull) return emptyList()
        val result = mutableListOf<Map<String, String>>()
        when {
            examplesNode is ArrayNode -> {
                for (item in examplesNode) {
                    when {
                        item.isObject -> {
                            val es = item.path("es").asText(null) ?: item.path("spanish").asText(null)
                            val en = item.path("en").asText(null) ?: item.path("english").asText(null)
                            if (es != null && en != null) {
                                result.add(mapOf("es" to es, "en" to en))
                            }
                        }
                        item.isTextual -> {
                            val parts = item.asText().split("|")
                            if (parts.size >= 2) {
                                result.add(mapOf("es" to parts[0].trim(), "en" to parts[1].trim()))
                            }
                        }
                    }
                }
            }
            examplesNode.isObject -> {
                val es = examplesNode.path("es").asText(null)
                val en = examplesNode.path("en").asText(null)
                if (es != null && en != null) {
                    result.add(mapOf("es" to es, "en" to en))
                }
            }
            examplesNode.isTextual -> {
                val lines = examplesNode.asText().split("\n")
                for (line in lines) {
                    val parts = line.split("|")
                    if (parts.size >= 2) {
                        result.add(mapOf("es" to parts[0].trim(), "en" to parts[1].trim()))
                    }
                }
            }
        }
        return result
    }

    private fun normalizeLevel(explicit: String?, inferred: String): String {
        val value = (explicit ?: inferred).uppercase(Locale.ENGLISH)
        val allowed = setOf("A1", "A2", "B1", "B2", "C1", "C2", "UNSET")
        return if (value in allowed) value else "UNSET"
    }

    fun inferLevelFromPath(path: Path): String {
        val tokens = path.toString().split('/', '-', '_', '.')
        for (token in tokens) {
            val upper = token.uppercase(Locale.ENGLISH)
            if (upper.matches("[ABC][12]".toRegex())) {
                return upper
            }
            if (upper.startsWith("LEVEL")) {
                val suffix = upper.removePrefix("LEVEL")
                if (suffix.matches("[ABC][12]".toRegex())) {
                    return suffix
                }
            }
        }
        return "UNSET"
    }
}
