/// @function scr_filter_seeders(_seeders, _q)
/// @description Case-insensitive filter on seeder id/title.
/// @param {array} _seeders
/// @param {string} _q
function scr_filter_seeders(_seeders, _q) {
    if (!is_array(_seeders)) {
        return [];
    }
    var q = "";
    if (!is_undefined(_q)) {
        q = string_lower(string(_q));
    }
    if (q == "") {
        return _seeders;
    }
    var out = [];
    for (var i = 0; i < array_length(_seeders); i++) {
        var m = _seeders[i];
        if (!is_ds_map(m)) {
            continue;
        }
        var id = "";
        if (ds_map_exists(m, "id")) {
            id = string_lower(string(ds_map_find_value(m, "id")));
        }
        var title = "";
        if (ds_map_exists(m, "title")) {
            title = string_lower(string(ds_map_find_value(m, "title")));
        }
        if (string_pos(q, id) > 0 || string_pos(q, title) > 0) {
            array_push(out, m);
        }
    }
    return out;
}
