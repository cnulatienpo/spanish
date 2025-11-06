/// @function scr_diff_lines(_a, _b)
/// @description Build a simple line-by-line diff list between two strings.
/// @param {string} _a
/// @param {string} _b
/// @returns {ds_list} entries where each entry is a ds_map with keys "type" and "text".
function scr_diff_lines(_a, _b) {
    var text_a = is_string(_a) ? _a : "";
    var text_b = is_string(_b) ? _b : "";
    var lines_a = string_split(text_a, "\n");
    var lines_b = string_split(text_b, "\n");
    var len_a = array_length(lines_a);
    var len_b = array_length(lines_b);
    var max_len = max(len_a, len_b);

    var diff = ds_list_create();

    for (var i = 0; i < max_len; i++) {
        var line_a = (i < len_a) ? lines_a[i] : "";
        var line_b = (i < len_b) ? lines_b[i] : "";

        if (line_a == line_b) {
            var same = ds_map_create();
            ds_map_set(same, "type", " ");
            ds_map_set(same, "text", line_a);
            ds_list_add(diff, same);
        } else {
            if (line_a != "") {
                var removed = ds_map_create();
                ds_map_set(removed, "type", "-");
                ds_map_set(removed, "text", line_a);
                ds_list_add(diff, removed);
            }
            if (line_b != "") {
                var added = ds_map_create();
                ds_map_set(added, "type", "+");
                ds_map_set(added, "text", line_b);
                ds_list_add(diff, added);
            }
        }
    }

    return diff;
}
