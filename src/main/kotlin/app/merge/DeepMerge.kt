package app.merge

import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.node.ArrayNode
import com.fasterxml.jackson.databind.node.JsonNodeFactory
import com.fasterxml.jackson.databind.node.ObjectNode

private val MERGE_SEPARATOR = "\n\n— MERGED VARIANT —\n\n"

data class MergeContext(
    val leftMtime: Long,
    val rightMtime: Long,
    val losingNotes: MutableList<String> = mutableListOf()
)

object DeepMerge {
    private val factory = JsonNodeFactory.instance

    fun merge(left: JsonNode, right: JsonNode, context: MergeContext): JsonNode {
        if (left.isObject && right.isObject) {
            return mergeObjects(left as ObjectNode, right as ObjectNode, context)
        }
        if (left.isArray && right.isArray) {
            return mergeArrays(left as ArrayNode, right as ArrayNode)
        }
        if (left.isTextual && right.isTextual) {
            if (left.asText() == right.asText()) {
                return left
            }
            val merged = mergePreferredScalar(left.asText(), right.asText(), context)
            return factory.textNode(merged)
        }
        return preferWithFallback(left, right, context)
    }

    private fun mergeObjects(left: ObjectNode, right: ObjectNode, context: MergeContext): ObjectNode {
        val result = left.deepCopy()
        val fieldNames = (left.fieldNames().asSequence().toSet() + right.fieldNames().asSequence().toSet()).sorted()
        for (name in fieldNames) {
            val l = left.get(name)
            val r = right.get(name)
            when {
                l == null -> result.set<JsonNode>(name, r)
                r == null -> result.set<JsonNode>(name, l)
                else -> {
                    if (name in setOf("definition", "origin", "story")) {
                        val concatenated = concatenateNarrative(l, r)
                        result.set<JsonNode>(name, concatenated)
                        continue
                    }
                    val merged = merge(l, r, context)
                    result.set<JsonNode>(name, merged)
                    if (merged == l && l != r && name != "notes" && r != null) {
                        appendAltVariant(result, name, r)
                    } else if (merged == r && l != r && name != "notes" && l != null) {
                        appendAltVariant(result, name, l)
                    }
                }
            }
        }
        return result
    }

    private fun concatenateNarrative(left: JsonNode, right: JsonNode): JsonNode {
        val leftText = textOf(left)
        val rightText = textOf(right)
        if (leftText == rightText) return factory.textNode(leftText)
        val merged = listOf(leftText, rightText).filter { it.isNotBlank() }.distinct()
        return factory.textNode(merged.joinToString(MERGE_SEPARATOR))
    }

    private fun textOf(node: JsonNode?): String = when {
        node == null -> ""
        node.isTextual -> node.asText()
        else -> node.toString()
    }

    private fun appendAltVariant(result: ObjectNode, field: String, losing: JsonNode) {
        val existingNotes = result.get("notes")?.asText() ?: ""
        val losingText = textOf(losing)
        if (losingText.isBlank()) return
        val addition = "${field}: ${losingText}"
        val updated = if (existingNotes.isBlank()) addition else existingNotes + "\n" + addition
        result.put("notes", updated)
    }

    private fun mergeArrays(left: ArrayNode, right: ArrayNode): ArrayNode {
        val result = factory.arrayNode()
        val existing = mutableListOf<JsonNode>()
        for (item in left) {
            result.add(item)
            existing.add(item)
        }
        for (item in right) {
            if (!containsEquivalent(existing, item)) {
                result.add(item)
                existing.add(item)
            }
        }
        return result
    }

    private fun containsEquivalent(list: List<JsonNode>, candidate: JsonNode): Boolean {
        return list.any { existing -> normalizeForComparison(existing) == normalizeForComparison(candidate) }
    }

    private fun normalizeForComparison(node: JsonNode): String {
        return when {
            node.isTextual -> node.asText().trim().replace("\\s+".toRegex(), " ")
            node.isObject -> node.fields().asSequence().joinToString("|") { (k, v) -> "$k=${normalizeForComparison(v)}" }
            node.isArray -> node.joinToString("|") { normalizeForComparison(it) }
            else -> node.toString()
        }
    }

    private fun preferWithFallback(left: JsonNode, right: JsonNode, context: MergeContext): JsonNode {
        val chooseRight = when {
            context.rightMtime > context.leftMtime -> true
            context.rightMtime < context.leftMtime -> false
            else -> textLength(right) >= textLength(left)
        }
        return if (chooseRight) right else left
    }

    private fun mergePreferredScalar(left: String, right: String, context: MergeContext): String {
        val chooseRight = when {
            context.rightMtime > context.leftMtime -> true
            context.rightMtime < context.leftMtime -> false
            else -> right.length >= left.length
        }
        return if (chooseRight) right else left
    }

    private fun textLength(node: JsonNode): Int = when {
        node.isTextual -> node.asText().length
        else -> node.toString().length
    }

    fun unionSourceLists(existing: List<String>, incoming: List<String>): List<String> {
        return (existing + incoming).toSet().toList().sorted()
    }
}
