/// @description Initialize global data and load profile + seeders.
function oApp_Create() {
    global.seeders = scr_load_seeders();
    global.profile = scr_profile_load();
    if (!is_array(global.seeders) || array_length(global.seeders) == 0) {
        show_debug_message("No seeders found. Please add data/seeders JSON files.");
        global.current_seeder = -1;
    } else {
        global.current_seeder = scr_pick_seeder(global.seeders, global.profile);
    }
}
