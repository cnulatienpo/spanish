/// @description Render typing HUD details with theming and settings controls.
function oTyping_DrawGUI() {
    var target_label = "Target: N/A";
    var expected_register = "Register: —";
    if (is_ds_map(global.current_seeder)) {
        target_label = scr_target_label(global.current_seeder);
        expected_register = scr_register_label(global.current_seeder);
    }

    if (!is_struct(global.settings)) {
        scr_settings_defaults();
    }
    var settings = global.settings;
    var font_scale = settings.font_scale;
    var high_contrast = settings.theme_high_contrast;
    var text_col = high_contrast ? c_white : c_white;
    var subhead_col = high_contrast ? c_white : c_silver;
    var background_col = high_contrast ? c_black : make_color_rgb(24, 24, 32);
    var button_base = high_contrast ? make_color_rgb(220, 220, 220) : c_dkgray;
    var button_hover = high_contrast ? make_color_rgb(255, 255, 255) : make_color_hsv(210, 20, 60);
    var button_text = high_contrast ? c_black : c_white;
    var chip_base = high_contrast ? make_color_rgb(70, 70, 70) : make_color_rgb(50, 50, 50);
    var chip_hover = high_contrast ? make_color_rgb(110, 110, 110) : merge_color(chip_base, c_white, 0.15);
    var chip_text = high_contrast ? c_white : c_white;

    draw_set_font(f_ui);
    draw_set_halign(fa_left);
    draw_set_valign(fa_top);

    var gui_w = display_get_gui_width();
    var gui_h = display_get_gui_height();

    draw_set_color(background_col);
    draw_rectangle(0, 0, gui_w, gui_h, false);

    draw_set_color(text_col);

    var draw_text_scaled = function(_x, _y, _text) {
        draw_text_transformed(_x, _y, _text, font_scale, font_scale, 0);
    };

    var settings_active = scr_settings_is_active();
    var mx = device_mouse_x_to_gui(0);
    var my = device_mouse_y_to_gui(0);
    var mouse_clicked = mouse_check_button_pressed(mb_left);
    var clicked = !settings_active && mouse_clicked;

    var bx = gui_w - 160;
    var by = 16;
    var bw = 110;
    var bh = 32;
    var back_hover = point_in_rectangle(mx, my, bx, by, bx + bw, by + bh);

    draw_set_color(back_hover ? button_hover : button_base);
    draw_rectangle(bx, by, bx + bw, by + bh, false);
    draw_set_color(c_black);
    draw_rectangle(bx, by, bx + bw, by + bh, true);
    draw_set_color(button_text);
    draw_set_halign(fa_center);
    draw_set_valign(fa_middle);
    draw_text_transformed(bx + bw * 0.5, by + bh * 0.5, "Back", font_scale, font_scale, 0);
    draw_set_halign(fa_left);
    draw_set_valign(fa_top);
    draw_set_color(text_col);

    if (clicked && back_hover) {
        room_goto(r_select);
        return;
    }

    var gear_size = 24;
    var gear_x = bx - gear_size - 12;
    var gear_y = 16;
    var gear_hover = point_in_rectangle(mx, my, gear_x, gear_y, gear_x + gear_size, gear_y + gear_size);
    draw_set_color(gear_hover ? button_hover : button_base);
    draw_rectangle(gear_x, gear_y, gear_x + gear_size, gear_y + gear_size, false);
    draw_set_color(c_black);
    draw_rectangle(gear_x, gear_y, gear_x + gear_size, gear_y + gear_size, true);
    draw_set_color(button_text);
    draw_set_halign(fa_center);
    draw_set_valign(fa_middle);
    draw_text_transformed(gear_x + gear_size * 0.5, gear_y + gear_size * 0.5, "⚙", font_scale, font_scale, 0);
    draw_set_halign(fa_left);
    draw_set_valign(fa_top);
    draw_set_color(text_col);

    if (mouse_clicked && gear_hover && object_exists(oSettings)) {
        with (oSettings) active = !active;
    }

    draw_text_scaled(20, 120, target_label);
    draw_text_scaled(20, 140, "Used: " + string(scr_count_spanish_tokens(input_text, [])));
    draw_text_scaled(20, 160, expected_register);
    draw_text_scaled(20, 180, "You: " + scr_detect_register(input_text));
    draw_text_scaled(20, 200, "Ratio: " + string_format(scr_spanish_ratio(input_text) * 100, 0, 2) + "%");
    draw_text_scaled(20, 220, feedback_text);

    var W = gui_w;
    var pad = 20;

    var user_reg = scr_detect_register(input_text);
    var expected = hint_expected;

    draw_set_color(subhead_col);
    draw_text_scaled(pad, 280, "Hint (register: " + string(expected) + ")");

    if (expected != "neutral" && user_reg != "neutral" && user_reg != expected) {
        draw_set_color(high_contrast ? make_color_rgb(255, 255, 0) : make_color_rgb(255, 210, 120));
        draw_text_scaled(pad, 300, "Try " + expected + " forms here (click a chip).");
    }

    var chips = hint_chips;
    if (!is_array(chips)) {
        chips = [];
    }

    var x0 = pad;
    var y0 = 324;
    var chip_h = 26;
    var chip_pad = 8;

    for (var i = 0; i < array_length(chips); i++) {
        var txt = chips[i];
        var tw = string_width(txt) * font_scale;
        var cw = tw + 20;

        var x1 = x0;
        var y1 = y0;
        var x2 = x1 + cw;
        var y2 = y1 + chip_h;

        if (x2 > W - pad) {
            x0 = pad;
            y0 += chip_h + 8;
            x1 = x0;
            y1 = y0;
            x2 = x1 + cw;
            y2 = y1 + chip_h;
        }

        var hover = point_in_rectangle(mx, my, x1, y1, x2, y2);
        var base_col = chip_base;
        if (i == hint_idx) {
            base_col = merge_color(base_col, c_white, 0.25);
        }
        if (hover) {
            base_col = chip_hover;
        }

        draw_set_color(base_col);
        draw_rectangle(x1, y1, x2, y2, false);
        draw_set_color(c_black);
        draw_rectangle(x1, y1, x2, y2, true);

        draw_set_color(chip_text);
        draw_set_halign(fa_left);
        draw_set_valign(fa_top);
        draw_text_transformed(x1 + 10, y1 + 4, txt, font_scale, font_scale, 0);

        if (clicked && hover) {
            scr_insert_phrase(txt);
        }

        x0 = x2 + chip_pad;
    }

    draw_set_halign(fa_left);
    draw_set_valign(fa_top);
    draw_set_color(text_col);

    scr_draw_mix_meter(global.current_seeder, input_text);

    if (settings.accent_strip_on) {
        var strip_y = display_get_gui_height() - 60;
        scr_draw_accent_strip(20, strip_y);
    }
}
