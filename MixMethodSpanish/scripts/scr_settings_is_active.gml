/// @function scr_settings_is_active()
/// @description Check if the pause/settings overlay is currently active.
function scr_settings_is_active() {
    if (!object_exists(oSettings)) {
        return false;
    }
    var inst = instance_find(oSettings, 0);
    if (inst == noone) {
        return false;
    }
    return inst.active;
}
