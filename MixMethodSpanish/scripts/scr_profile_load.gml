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
    var profile;
    var settings_source = undefined;

    if (is_struct(parsed)) {
        if (!variable_struct_exists(parsed, "xp")) parsed.xp = 0;
        if (!variable_struct_exists(parsed, "mix_ratio")) parsed.mix_ratio = 0.15;
        if (!variable_struct_exists(parsed, "register_bonus")) parsed.register_bonus = 0;
        if (!variable_struct_exists(parsed, "seen")) parsed.seen = [];
        if (!variable_struct_exists(parsed, "last_selected_id")) parsed.last_selected_id = "";
        if (variable_struct_exists(parsed, "settings")) {
            settings_source = parsed.settings;
        }
        profile = parsed;
    } else if (is_ds_map(parsed)) {
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
        if (ds_map_exists(parsed, "settings")) {
            settings_source = ds_map_find_value(parsed, "settings");
        }
        ds_map_destroy(parsed);
        profile = prof;
    } else {
        return scr_profile_default();
    }

    var settings_struct = {};
    if (is_struct(settings_source)) {
        settings_struct = settings_source;
    } else if (is_ds_map(settings_source)) {
        settings_struct = {
            font_scale: ds_map_exists(settings_source, "font_scale") ? real(ds_map_find_value(settings_source, "font_scale")) : 1.0,
            theme_high_contrast: ds_map_exists(settings_source, "theme_high_contrast") ? ds_map_find_value(settings_source, "theme_high_contrast") : false,
            sfx_volume: ds_map_exists(settings_source, "sfx_volume") ? real(ds_map_find_value(settings_source, "sfx_volume")) : 0.8,
            accent_strip_on: ds_map_exists(settings_source, "accent_strip_on") ? ds_map_find_value(settings_source, "accent_strip_on") : true
        };
        ds_map_destroy(settings_source);
    }

    global.settings = settings_struct;
    scr_settings_defaults();
    profile.settings = global.settings;
    return profile;
}

/// @function scr_profile_default()
/// @description Provide a default profile struct.
function scr_profile_default() {
    global.settings = {};
    scr_settings_defaults();
    return {
        xp: 0,
        mix_ratio: 0.15,
        register_bonus: 0,
        seen: [],
        last_selected_id: "",
        settings: global.settings,
    };
}
