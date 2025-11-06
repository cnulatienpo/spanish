/// @function scr_draw_accent_strip(_x, _y)
/// @description Draw accent character buttons that append to keyboard input.
/// @param {real} _x
/// @param {real} _y
function scr_draw_accent_strip(_x, _y) {
    if (!is_struct(global.settings)) {
        scr_settings_defaults();
    }
    var settings = global.settings;
    var font_scale = settings.font_scale;
    var high_contrast = settings.theme_high_contrast;

    var chars = ["á", "é", "í", "ó", "ú", "ñ", "¿", "¡"];
    var pad = 8;
    var w = 32;
    var h = 32;
    var mx = device_mouse_x_to_gui(0);
    var my = device_mouse_y_to_gui(0);

    draw_set_font(f_ui);
    draw_set_halign(fa_center);
    draw_set_valign(fa_middle);

    for (var i = 0; i < array_length(chars); i++) {
        var cx = _x + (w + pad) * i;
        var cy = _y;
        var rect_col = high_contrast ? make_color_rgb(30, 30, 30) : c_dkgray;
        var hover_col = high_contrast ? make_color_rgb(200, 200, 200) : c_gray;
        var text_col = high_contrast ? c_white : c_white;

        if (point_in_rectangle(mx, my, cx, cy, cx + w, cy + h)) {
            rect_col = hover_col;
            if (mouse_check_button_pressed(mb_left)) {
                keyboard_string += chars[i];
                input_text = keyboard_string;
            }
        }

        draw_set_color(rect_col);
        draw_rectangle(cx, cy, cx + w, cy + h, false);
        draw_set_color(c_black);
        draw_rectangle(cx, cy, cx + w, cy + h, true);
        draw_set_color(text_col);
        draw_text_transformed(cx + w * 0.5, cy + h * 0.5, chars[i], font_scale, font_scale, 0);
    }
    draw_set_halign(fa_left);
    draw_set_valign(fa_top);
}
