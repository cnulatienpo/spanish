/// @function scr_validate_all_seeders(_seeders)
/// @description Validate all seeders and collect errors keyed by ID (duplicates flagged).
/// @param {array<ds_map>} _seeders
/// @returns {ds_map<string, ds_list>} errors_by_id
function scr_validate_all_seeders(_seeders) {
    var out = ds_map_create();
    var seen = ds_map_create();

    if (!is_array(_seeders)) {
        return out;
    }

    for (var i = 0; i < array_length(_seeders); i++) {
        var m = _seeders[i];
        var id = "";
        if (is_ds_map(m) && ds_map_exists(m, "id")) {
            id = string(ds_map_find_value(m, "id"));
        }
        var key = (id != "") ? id : "(no-id-" + string(i) + ")";
        if (is_ds_map(m)) {
            ds_map_set(m, "__validator_key", key);
        }
        if (ds_map_exists(out, key)) {
            var prev = ds_map_find_value(out, key);
            if (is_ds_list(prev)) {
                ds_list_destroy(prev);
            }
        }
        var errs = scr_validate_seeder(m);
        ds_map_set(out, key, errs);

        var c = ds_map_exists(seen, key) ? ds_map_find_value(seen, key) : 0;
        ds_map_set(seen, key, c + 1);
    }

    var it = ds_map_create_iterator(seen);
    while (ds_map_iterator_is_ok(it)) {
        var k = ds_map_iterator_key(it);
        var n = ds_map_iterator_value(it);
        if (n > 1) {
            var lst = ds_map_find_value(out, k);
            if (is_ds_list(lst)) {
                ds_list_add(lst, "Duplicate 'id' appears " + string(n) + " times");
            }
        }
        ds_map_iterator_next(it);
    }
    ds_map_destroy_iterator(it);
    ds_map_destroy(seen);

    return out;
}
