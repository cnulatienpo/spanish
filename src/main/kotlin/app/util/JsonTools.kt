package app.util

import com.fasterxml.jackson.core.JsonFactoryBuilder
import com.fasterxml.jackson.core.JsonParser
import com.fasterxml.jackson.databind.DeserializationFeature
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.databind.SerializationFeature
import com.fasterxml.jackson.databind.node.ObjectNode
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.registerKotlinModule

object JsonTools {
    val mapper: ObjectMapper = jacksonObjectMapper().apply {
        configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
        configure(DeserializationFeature.ACCEPT_SINGLE_VALUE_AS_ARRAY, true)
        configure(DeserializationFeature.ACCEPT_EMPTY_STRING_AS_NULL_OBJECT, true)
        enable(SerializationFeature.INDENT_OUTPUT)
    }

    val orderingMapper: ObjectMapper = ObjectMapper(
        JsonFactoryBuilder().build()
    ).registerKotlinModule().apply {
        configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true)
        configure(SerializationFeature.INDENT_OUTPUT, true)
        configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
    }

    fun toSortedObjectNode(node: ObjectNode): ObjectNode {
        val fieldNames = node.fieldNames().asSequence().toList().sorted()
        val sorted = mapper.createObjectNode()
        for (name in fieldNames) {
            val value = node.get(name)
            sorted.set<ObjectNode>(name, when (value) {
                is ObjectNode -> toSortedObjectNode(value)
                else -> value
            })
        }
        return sorted
    }

    fun newParser(json: String): JsonParser = mapper.factory.createParser(json)
}
