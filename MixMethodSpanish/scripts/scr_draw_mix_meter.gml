/// @function scr_draw_mix_meter(_seeder, _input)
/// @description Draw the mix progress meter for the current typing stage.
/// @param {ds_map|undefined} _seeder
/// @param {string} _input
function scr_draw_mix_meter(_seeder, _input) {
    var cefr = "A0";
    var mix = undefined;
    if (is_ds_map(_seeder)) {
        if (ds_map_exists(_seeder, "cefr")) {
            cefr = ds_map_find_value(_seeder, "cefr");
        }
        if (ds_map_exists(_seeder, "mix")) {
            mix = ds_map_find_value(_seeder, "mix");
        }
    }

    var min = (is_ds_map(mix) && ds_map_exists(mix, "min_tokens"))
        ? ds_map_find_value(mix, "min_tokens")
        : scr_mix_cefr_default_min(cefr);

    var used = scr_count_spanish_tokens(_input, []);
    var ratio = scr_spanish_ratio(_input);
    var target_ratio = (cefr == "C1") ? 0.4 : (cefr == "C2") ? 0.6 : 0;

    var pct;
    if (cefr == "C1" || cefr == "C2") {
        pct = (target_ratio > 0) ? ratio / target_ratio : 0;
    } else {
        pct = used / max(1, min);
    }
    pct = clamp(pct, 0, 1.5);

    var col;
    if (pct < 0.5) {
        col = make_color_rgb(200, 60, 60);
    } else if (pct < 1) {
        col = make_color_rgb(240, 180, 40);
    } else {
        col = make_color_rgb(60, 200, 100);
    }

    if (pct >= 1) {
        var pulse = 0.7 + 0.3 * abs(sin(current_time / 200));
        col = merge_color(col, c_white, pulse * 0.2);
    }

    if (!is_struct(global.settings)) {
        scr_settings_defaults();
    }
    var settings = global.settings;
    var font_scale = settings.font_scale;
    var high_contrast = settings.theme_high_contrast;
    var bar_bg = high_contrast ? make_color_rgb(30, 30, 30) : make_color_rgb(40, 40, 40);
    var text_col = high_contrast ? c_white : c_white;

    var gui_w = display_get_gui_width();
    var gui_h = display_get_gui_height();
    var bx = 20;
    var by = gui_h - 100;
    var bw = gui_w - 40;
    var bh = 20;

    draw_set_color(bar_bg);
    draw_rectangle(bx, by, bx + bw, by + bh, false);

    var fill = clamp(pct, 0, 1) * bw;
    draw_set_color(col);
    draw_rectangle(bx, by, bx + fill, by + bh, false);

    draw_set_color(text_col);
    draw_set_font(f_ui);
    draw_set_halign(fa_center);
    draw_set_valign(fa_middle);

    var label;
    if (cefr == "C1" || cefr == "C2") {
        label = string_format(ratio * 100, 0, 1) + "%  Spanish";
    } else {
        label = string(used) + " / " + string(min) + "  Spanish words";
    }

    draw_text_transformed(bx + bw * 0.5, by + bh * 0.5, label, font_scale, font_scale, 0);

    draw_set_halign(fa_left);
    draw_set_valign(fa_top);
}
