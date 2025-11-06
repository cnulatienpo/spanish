/// @description Render the settings overlay when active.
function oSettings_DrawGUI() {
    if (!active) {
        return;
    }

    var settings = global.settings;
    var font_scale = settings.font_scale;
    var high_contrast = settings.theme_high_contrast;

    var W = display_get_gui_width();
    var H = display_get_gui_height();

    var backdrop_col = high_contrast ? c_black : make_color_rgb(30, 30, 40);
    var panel_col = high_contrast ? c_white : make_color_rgb(60, 60, 70);
    var panel_outline = high_contrast ? c_black : make_color_rgb(10, 10, 10);
    var text_col = high_contrast ? c_black : c_white;
    var slider_bg = high_contrast ? make_color_rgb(220, 220, 220) : c_dkgray;
    var slider_fill = high_contrast ? c_black : c_white;
    var toggle_on = high_contrast ? make_color_rgb(20, 20, 20) : c_lime;
    var toggle_off = high_contrast ? make_color_rgb(160, 160, 160) : c_gray;
    var toggle_text_on = high_contrast ? c_white : c_black;
    var toggle_text_off = high_contrast ? c_black : c_black;

    draw_set_alpha(0.85);
    draw_set_color(backdrop_col);
    draw_rectangle(0, 0, W, H, false);
    draw_set_alpha(1);

    var pw = min(480, W - 40);
    var ph = min(420, H - 80);
    var px = (W - pw) * 0.5;
    var py = (H - ph) * 0.5;

    draw_set_color(panel_col);
    draw_rectangle(px, py, px + pw, py + ph, false);
    draw_set_color(panel_outline);
    draw_rectangle(px, py, px + pw, py + ph, true);

    draw_set_font(f_ui);
    draw_set_color(text_col);
    draw_set_halign(fa_left);
    draw_set_valign(fa_top);

    var draw_text_scaled = function(_x, _y, _text) {
        draw_text_transformed(_x, _y, _text, font_scale, font_scale, 0);
    };

    draw_text_scaled(px + 20, py + 20, "⚙ Settings");

    draw_text_scaled(px + 20, py + 70, "Font Size (" + string_format(settings.font_scale, 0, 2) + ")");
    var bx = px + 160;
    var by = py + 90;
    var bw = 200;
    var bh = 12;
    draw_set_color(slider_bg);
    draw_rectangle(bx, by, bx + bw, by + bh, false);
    draw_set_color(panel_outline);
    draw_rectangle(bx, by, bx + bw, by + bh, true);
    draw_set_color(slider_fill);
    var font_pct = (settings.font_scale - 0.8) / 0.8;
    draw_rectangle(bx, by, bx + clamp(font_pct, 0, 1) * bw, by + bh, false);

    draw_text_scaled(px + 20, py + 140, "SFX Volume (" + string_format(settings.sfx_volume, 0, 2) + ")");
    by = py + 160;
    draw_set_color(slider_bg);
    draw_rectangle(bx, by, bx + bw, by + bh, false);
    draw_set_color(panel_outline);
    draw_rectangle(bx, by, bx + bw, by + bh, true);
    draw_set_color(slider_fill);
    draw_rectangle(bx, by, bx + clamp(settings.sfx_volume, 0, 1) * bw, by + bh, false);

    draw_text_scaled(px + 20, py + 210, "High Contrast");
    var toggle_x = px + 200;
    var toggle_y = py + 210;
    var toggle_w = 120;
    var toggle_h = 28;
    draw_set_color(settings.theme_high_contrast ? toggle_on : toggle_off);
    draw_rectangle(toggle_x, toggle_y, toggle_x + toggle_w, toggle_y + toggle_h, false);
    draw_set_color(panel_outline);
    draw_rectangle(toggle_x, toggle_y, toggle_x + toggle_w, toggle_y + toggle_h, true);
    draw_set_halign(fa_center);
    draw_set_valign(fa_middle);
    draw_set_color(settings.theme_high_contrast ? toggle_text_on : toggle_text_off);
    draw_text_transformed(toggle_x + toggle_w * 0.5, toggle_y + toggle_h * 0.5, settings.theme_high_contrast ? "On" : "Off", font_scale, font_scale, 0);

    draw_set_halign(fa_left);
    draw_set_valign(fa_top);
    draw_set_color(text_col);
    draw_text_scaled(px + 20, py + 260, "Accent Strip");
    toggle_y = py + 260;
    draw_set_color(settings.accent_strip_on ? toggle_on : toggle_off);
    draw_rectangle(toggle_x, toggle_y, toggle_x + toggle_w, toggle_y + toggle_h, false);
    draw_set_color(panel_outline);
    draw_rectangle(toggle_x, toggle_y, toggle_x + toggle_w, toggle_y + toggle_h, true);
    draw_set_halign(fa_center);
    draw_set_valign(fa_middle);
    draw_set_color(settings.accent_strip_on ? toggle_text_on : toggle_text_off);
    draw_text_transformed(toggle_x + toggle_w * 0.5, toggle_y + toggle_h * 0.5, settings.accent_strip_on ? "On" : "Off", font_scale, font_scale, 0);

    draw_set_halign(fa_left);
    draw_set_valign(fa_top);
    draw_set_color(text_col);
    draw_text_scaled(px + pw - 200, py + ph - 40, "Press ESC to close");
}
