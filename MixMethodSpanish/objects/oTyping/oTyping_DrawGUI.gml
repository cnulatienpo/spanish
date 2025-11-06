/// @description Render typing HUD details.
function oTyping_DrawGUI() {
    var target_label = "Target: N/A";
    var expected_register = "Register: —";
    if (is_ds_map(global.current_seeder)) {
        target_label = scr_target_label(global.current_seeder);
        expected_register = scr_register_label(global.current_seeder);
    }

    draw_set_font(f_ui);
    draw_set_color(c_white);
    draw_set_halign(fa_left);

    var gui_w = display_get_gui_width();
    var bx = gui_w - 120;
    var by = 16;
    var bw = 100;
    var bh = 28;

    var mx = device_mouse_x_to_gui(0);
    var my = device_mouse_y_to_gui(0);
    var hover = point_in_rectangle(mx, my, bx, by, bx + bw, by + bh);

    draw_set_color(hover ? make_color_hsv(210, 20, 60) : c_dkgray);
    draw_rectangle(bx, by, bx + bw, by + bh, false);
    draw_set_color(c_white);
    draw_set_halign(fa_center);
    draw_text(bx + bw / 2, by + bh / 2 - 6, "Back");
    draw_set_halign(fa_left);

    if (mouse_check_button_pressed(mb_left) && hover) {
        room_goto(r_select);
        return;
    }

    draw_text(20, 120, target_label);
    draw_text(20, 140, "Used: " + string(scr_count_spanish_tokens(input_text, [])));
    draw_text(20, 160, expected_register);
    draw_text(20, 180, "You: " + scr_detect_register(input_text));
    draw_text(20, 200, "Ratio: " + string_format(scr_spanish_ratio(input_text) * 100, 0, 2) + "%");
    draw_text(20, 220, feedback_text);

    // ---------- Register Hints UI ----------
    var W = display_get_gui_width();
    var pad = 20;

    var user_reg = scr_detect_register(input_text);
    var expected = hint_expected;

    draw_set_color(c_silver);
    draw_set_font(f_ui);
    draw_set_halign(fa_left);

    var head = "Hint (register: " + string(expected) + ")";
    draw_text(pad, 280, head);

    if (expected != "neutral" && user_reg != "neutral" && user_reg != expected) {
        draw_set_color(make_color_rgb(255, 210, 120));
        draw_text(pad, 300, "Try " + expected + " forms here (click a chip).");
    }

    var clicked = mouse_check_button_pressed(mb_left);

    var x0 = pad;
    var y0 = 324;
    var chip_h = 26;
    var chip_pad = 8;
    var chips = hint_chips;
    if (!is_array(chips)) {
        chips = [];
    }

    for (var i = 0; i < array_length(chips); i++) {
        var txt = chips[i];
        var tw = string_width(txt);
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

        var base_col = make_color_rgb(50, 50, 50);
        if (i == hint_idx) {
            base_col = merge_color(base_col, c_white, 0.25);
        }
        if (hover) {
            base_col = merge_color(base_col, c_white, 0.15);
        }

        draw_set_color(base_col);
        draw_rectangle(x1, y1, x2, y2, false);

        draw_set_color(c_white);
        draw_set_halign(fa_left);
        draw_text(x1 + 10, y1 + 4, txt);

        if (clicked && hover) {
            scr_insert_phrase(txt);
        }

        x0 = x2 + chip_pad;
    }

    scr_draw_mix_meter(global.current_seeder, input_text);
    var strip_y = display_get_gui_height() - 60;
    scr_draw_accent_strip(20, strip_y);
}
