/// @function scr_pick_seeder(_seeders, _profile)
/// @description Pick the next seeder prioritising unseen entries.
function scr_pick_seeder(_seeders, _profile) {
    if (!is_array(_seeders) || array_length(_seeders) == 0) {
        return -1;
    }
    var seen = [];
    if (is_struct(_profile) && variable_struct_exists(_profile, "seen")) {
        seen = _profile.seen;
    }
    for (var i = 0; i < array_length(_seeders); i++) {
        var seeder = _seeders[i];
        if (is_ds_map(seeder) && ds_map_exists(seeder, "id")) {
            var sid = ds_map_find_value(seeder, "id");
            if (!scr_array_contains(seen, sid)) {
                return seeder;
            }
        }
    }
    return _seeders[irandom(array_length(_seeders) - 1)];
}
