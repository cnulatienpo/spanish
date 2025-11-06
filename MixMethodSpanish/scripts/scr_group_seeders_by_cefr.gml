/// @function scr_group_seeders_by_cefr(_seeders)
/// @description Group seeders by CEFR band.
/// @param {array} _seeders
/// @returns {ds_map} Map of CEFR band -> array of seeder maps.
function scr_group_seeders_by_cefr(_seeders) {
    var out = ds_map_create();
    var bands = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"];
    for (var b = 0; b < array_length(bands); b++) {
        ds_map_set(out, bands[b], []);
    }
    if (!is_array(_seeders)) {
        return out;
    }
    for (var i = 0; i < array_length(_seeders); i++) {
        var m = _seeders[i];
        if (!is_ds_map(m)) {
            continue;
        }
        var c = "";
        if (ds_map_exists(m, "cefr")) {
            c = string_upper(ds_map_find_value(m, "cefr"));
        }
        if (!ds_map_exists(out, c)) {
            ds_map_set(out, c, []);
        }
        var arr = ds_map_find_value(out, c);
        array_push(arr, m);
    }
    return out;
}
