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
    scr_draw_mix_meter(global.current_seeder, input_text);
    var strip_y = display_get_gui_height() - 60;
    scr_draw_accent_strip(20, strip_y);
}
