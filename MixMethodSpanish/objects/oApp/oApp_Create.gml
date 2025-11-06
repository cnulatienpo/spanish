/// @description Initialize global data and load profile + seeders.
function oApp_Create() {
    global.seeders = scr_load_seeders();
    global.seeder_errors = scr_validate_all_seeders(global.seeders);
    global.profile = scr_profile_load();
    if (!is_struct(global.profile)) {
        global.profile = scr_profile_default();
    }
    scr_settings_defaults();

    var last_id = "";
    if (variable_struct_exists(global.profile, "last_selected_id")) {
        last_id = scr_set_last_selected_id(global.profile.last_selected_id);
    } else {
        last_id = scr_set_last_selected_id("");
    }

    global.current_seeder = -1;

    if (!is_array(global.seeders) || array_length(global.seeders) == 0) {
        show_debug_message("No seeders found. Please add data/seeders JSON files.");
    } else {
        var preferred = (last_id != "") ? scr_find_seeder_by_id(global.seeders, last_id) : -1;
        if (preferred != -1) {
            global.current_seeder = preferred;
            if (ds_map_exists(preferred, "id")) {
                scr_set_last_selected_id(ds_map_find_value(preferred, "id"));
            }
        } else {
            var picked = scr_pick_seeder(global.seeders, global.profile);
            if (picked != -1) {
                global.current_seeder = picked;
                if (ds_map_exists(picked, "id")) {
                    scr_set_last_selected_id(ds_map_find_value(picked, "id"));
                }
            }
        }
    }

    if (global.current_seeder == -1) {
        room_goto(r_select);
    } else {
        room_goto(r_typing);
    }
}
