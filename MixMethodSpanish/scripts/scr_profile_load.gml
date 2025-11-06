/// @function scr_profile_load()
/// @description Load or create the persistent profile JSON.
function scr_profile_load() {
    var path = "data/profile.json";
    if (!file_exists(path)) {
        return scr_profile_default();
    }
    var file = file_text_open_read(path);
    if (file == -1) {
        return scr_profile_default();
    }
    var json = "";
    while (!file_text_eof(file)) {
        json += file_text_read_string(file);
        if (!file_text_eof(file)) {
            json += "\n";
        }
    }
    file_text_close(file);
    if (json == "") {
        return scr_profile_default();
    }
    var parsed = json_parse(json);
    if (is_struct(parsed)) {
        if (!variable_struct_exists(parsed, "xp")) parsed.xp = 0;
        if (!variable_struct_exists(parsed, "mix_ratio")) parsed.mix_ratio = 0.15;
        if (!variable_struct_exists(parsed, "register_bonus")) parsed.register_bonus = 0;
        if (!variable_struct_exists(parsed, "seen")) parsed.seen = [];
        if (!variable_struct_exists(parsed, "last_selected_id")) parsed.last_selected_id = "";
        return parsed;
    }
    if (is_ds_map(parsed)) {
        var prof = {
            xp: ds_map_exists(parsed, "xp") ? ds_map_find_value(parsed, "xp") : 0,
            mix_ratio: ds_map_exists(parsed, "mix_ratio") ? ds_map_find_value(parsed, "mix_ratio") : 0.15,
            register_bonus: ds_map_exists(parsed, "register_bonus") ? ds_map_find_value(parsed, "register_bonus") : 0,
            seen: [],
            last_selected_id: ds_map_exists(parsed, "last_selected_id") ? string(ds_map_find_value(parsed, "last_selected_id")) : ""
        };
        if (ds_map_exists(parsed, "seen")) {
            var seen_list = ds_map_find_value(parsed, "seen");
            if (is_array(seen_list)) {
                prof.seen = seen_list;
            } else if (ds_exists(seen_list, ds_type_list)) {
                var len = ds_list_size(seen_list);
                var arr = [];
                for (var i = 0; i < len; i++) {
                    array_push(arr, ds_list_find_value(seen_list, i));
                }
                prof.seen = arr;
                ds_list_destroy(seen_list);
            }
        }
        ds_map_destroy(parsed);
        return prof;
    }
    return scr_profile_default();
}

/// @function scr_profile_default()
/// @description Provide a default profile struct.
function scr_profile_default() {
    return {
        xp: 0,
        mix_ratio: 0.15,
        register_bonus: 0,
        seen: [],
        last_selected_id: ""
    };
}
