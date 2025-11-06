/// @function scr_insert_phrase(_s)
/// @description Append the given phrase to keyboard_string with spacing.
/// @param {string} _s
function scr_insert_phrase(_s) {
    var cur = keyboard_string;
    if (string_length(cur) > 0 && string_char_at(cur, string_length(cur)) != " ") {
        cur += " ";
    }
    keyboard_string = cur + string(_s) + " ";
}
