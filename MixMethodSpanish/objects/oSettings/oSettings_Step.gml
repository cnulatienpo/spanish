/// @description Toggle and adjust settings via GUI interaction.
function oSettings_Step() {
    scr_settings_defaults();

    if (keyboard_check_pressed(vk_escape)) {
        active = !active;
        if (!active) {
            slider_drag = "";
        }
    }

    if (!active) {
        slider_drag = "";
        return;
    }

    var settings = global.settings;
    var mx = device_mouse_x_to_gui(0);
    var my = device_mouse_y_to_gui(0);
    var clicked = mouse_check_button_pressed(mb_left);
    var held = mouse_check_button(mb_left);
    var changed = false;

    var bx = 180;
    var by = 180;
    var bw = 200;
    var bh = 12;

    if (clicked && point_in_rectangle(mx, my, bx, by, bx + bw, by + bh)) {
        slider_drag = "font";
    }
    if (!held) {
        if (slider_drag == "font") {
            slider_drag = "";
        }
    }
    if (slider_drag == "font" && held) {
        var new_font = clamp((mx - bx) / bw * 0.8 + 0.8, 0.8, 1.6);
        if (abs(new_font - settings.font_scale) > 0.0005) {
            settings.font_scale = new_font;
            changed = true;
        }
    }

    by += 60;
    if (clicked && point_in_rectangle(mx, my, bx, by, bx + bw, by + bh)) {
        slider_drag = "sfx";
    }
    if (slider_drag == "sfx" && held) {
        var new_vol = clamp((mx - bx) / bw, 0, 1);
        if (abs(new_vol - settings.sfx_volume) > 0.0005) {
            settings.sfx_volume = new_vol;
            changed = true;
        }
    }
    if (!held && slider_drag == "sfx") {
        slider_drag = "";
    }

    if (clicked) {
        var ty = 180 + 120;
        if (point_in_rectangle(mx, my, 180, ty, 300, ty + 24)) {
            settings.theme_high_contrast = !settings.theme_high_contrast;
            changed = true;
        }
        ty += 40;
        if (point_in_rectangle(mx, my, 180, ty, 300, ty + 24)) {
            settings.accent_strip_on = !settings.accent_strip_on;
            changed = true;
        }
    }

    if (changed) {
        scr_settings_defaults();
        if (variable_global_exists("profile") && is_struct(global.profile)) {
            global.profile.settings = global.settings;
            scr_profile_save(global.profile);
        }
    }
}
