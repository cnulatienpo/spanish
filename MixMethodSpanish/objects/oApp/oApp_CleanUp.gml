/// @description Persist profile on shutdown.
function oApp_CleanUp() {
    if (is_struct(global.profile)) {
        scr_profile_save(global.profile);
    }
}
