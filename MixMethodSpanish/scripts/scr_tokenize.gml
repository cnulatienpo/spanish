/// @function scr_tokenize(_s)
/// @description Tokenize user input, normalizing punctuation and casing.
/// @param {string} _s - The source string to tokenize.
function scr_tokenize(_s) {
    var s = string_lower(_s);
    var punct = ".,!?;:\"()[]{}¿¡";
    for (var i = 1; i <= string_length(punct); i++) {
        var ch = string_char_at(punct, i);
        s = string_replace_all(s, ch, " ");
    }
    while (string_pos("  ", s) > 0) {
        s = string_replace_all(s, "  ", " ");
    }
    if (string_trim(s) == "") {
        return [];
    }
    return string_split(string_trim(s), " ");
}
