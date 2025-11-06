/// @function scr_count_spanish_tokens(_user, _expected_list)
/// @description Count Spanish tokens in the user response using heuristics and lexicon lookup.
/// @param {string} _user
/// @param {array} _expected_list
function scr_count_spanish_tokens(_user, _expected_list) {
    var toks = scr_tokenize(_user);
    var count = 0;
    var lex = scr_spanish_lexicon();
    for (var i = 0; i < array_length(toks); i++) {
        var w = toks[i];
        if (string_pos("áéíóúñ¿¡", w) > 0) {
            count++;
            continue;
        }
        for (var j = 0; j < array_length(lex); j++) {
            if (lex[j] == w) {
                count++;
                break;
            }
        }
    }
    return count;
}
