/// @function scr_settings_defaults()
/// @description Ensure the global settings struct exists with default values.
function scr_settings_defaults() {
    if (!variable_global_exists("settings") || !is_struct(global.settings)) {
        global.settings = {};
    }

    if (!variable_struct_exists(global.settings, "font_scale")) global.settings.font_scale = 1.0;
    if (!variable_struct_exists(global.settings, "theme_high_contrast")) global.settings.theme_high_contrast = false;
    if (!variable_struct_exists(global.settings, "sfx_volume")) global.settings.sfx_volume = 0.8;
    if (!variable_struct_exists(global.settings, "accent_strip_on")) global.settings.accent_strip_on = true;

    global.settings.font_scale = clamp(real(global.settings.font_scale), 0.8, 1.6);
    global.settings.sfx_volume = clamp(real(global.settings.sfx_volume), 0, 1);
    global.settings.theme_high_contrast = (global.settings.theme_high_contrast == true);
    global.settings.accent_strip_on = (global.settings.accent_strip_on != false);

    if (variable_global_exists("profile") && is_struct(global.profile)) {
        global.profile.settings = global.settings;
    }
}
