/// @function scr_find_seeder_by_id(_seeders, _id)
/// @description Locate a seeder map by id.
/// @param {array} _seeders
/// @param {string} _id
/// @returns {ds_map|real} ds_map when found, otherwise -1.
function scr_find_seeder_by_id(_seeders, _id) {
    if (!is_array(_seeders) || array_length(_seeders) == 0) {
        return -1;
    }
    if (is_undefined(_id) || string(_id) == "") {
        return -1;
    }
    var needle = string(_id);
    for (var i = 0; i < array_length(_seeders); i++) {
        var m = _seeders[i];
        if (!is_ds_map(m)) {
            continue;
        }
        if (!ds_map_exists(m, "id")) {
            continue;
        }
        if (string(ds_map_find_value(m, "id")) == needle) {
            return m;
        }
    }
    return -1;
}
