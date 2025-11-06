/// @description Initialize stage select UI state and data.
function oSelect_Create() {
    ui_pad = 16;
    card_h = 86;
    col_w = 480;
    gap_y = 10;
    section_markers = [];
    hide_invalid = false;

    if (!is_struct(global.profile)) {
        global.profile = scr_profile_load();
        if (!is_struct(global.profile)) {
            global.profile = scr_profile_default();
        }
    }
    if (!variable_struct_exists(global.profile, "last_selected_id")) {
        global.profile.last_selected_id = "";
    }

    var stored_id = global.profile.last_selected_id;
    if (is_undefined(stored_id) || stored_id == -1) {
        stored_id = "";
    }
    scr_set_last_selected_id(stored_id);

    if (!is_array(global.seeders) || array_length(global.seeders) == 0) {
        global.seeders = scr_load_seeders();
        global.seeder_errors = scr_validate_all_seeders(global.seeders);
    } else if (!is_ds_map(global.seeder_errors)) {
        global.seeder_errors = scr_validate_all_seeders(global.seeders);
    }
    all_seeders = is_array(global.seeders) ? global.seeders : [];

    search_q = "";
    scroll_y = 0;
    scroll_max = 0;
    preview_map = -1;
    sorted = [];

    selected_id = is_string(global.last_selected_id) ? global.last_selected_id : string(global.last_selected_id);
    if (selected_id == "-1") {
        selected_id = "";
    }

    if (selected_id != "") {
        var sel_map = scr_find_seeder_by_id(all_seeders, selected_id);
        if (sel_map != -1 && ds_map_exists(sel_map, "id")) {
            selected_id = string(ds_map_find_value(sel_map, "id"));
        } else {
            selected_id = "";
        }
    }

    if (selected_id == "" && is_ds_map(global.current_seeder) && ds_map_exists(global.current_seeder, "id")) {
        selected_id = string(ds_map_find_value(global.current_seeder, "id"));
    }

    var grouped = scr_group_seeders_by_cefr(all_seeders);
    if (is_ds_map(grouped)) {
        var bands = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"];
        for (var b = 0; b < array_length(bands); b++) {
            var band = bands[b];
            var arr = ds_map_exists(grouped, band) ? ds_map_find_value(grouped, band) : [];
            if (!is_array(arr) || array_length(arr) == 0) {
                continue;
            }
            array_sort(arr, function(a, b) {
                var at = ds_map_exists(a, "title") ? ds_map_find_value(a, "title") : "";
                var bt = ds_map_exists(b, "title") ? ds_map_find_value(b, "title") : "";
                return string_compare(at, bt);
            });
            var sec = ds_map_create();
            ds_map_set(sec, "__section", band);
            array_push(section_markers, sec);
            array_push(sorted, sec);
            for (var j = 0; j < array_length(arr); j++) {
                array_push(sorted, arr[j]);
            }
        }
        ds_map_destroy(grouped);
    }

    if (object_exists(oSettings) && !instance_exists(oSettings)) {
        instance_create_layer(0, 0, "Instances", oSettings);
    }

    if (object_exists(oBackupMgr) && !instance_exists(oBackupMgr)) {
        instance_create_layer(0, 0, "Instances", oBackupMgr);
    }
}
