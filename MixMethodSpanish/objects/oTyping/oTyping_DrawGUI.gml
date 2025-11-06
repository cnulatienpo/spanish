/// @description Render typing HUD details.
function oTyping_DrawGUI() {
    var target_label = "Target: N/A";
    if (is_ds_map(global.current_seeder)) {
        var cefr = ds_map_find_value(global.current_seeder, "cefr");
        if (cefr == "C1") {
            target_label = "Target: ≥40% Spanish tokens";
        } else if (cefr == "C2") {
            target_label = "Target: ≥60% Spanish tokens";
        } else {
            var min_tokens = scr_mix_cefr_default_min(cefr);
            if (ds_map_exists(global.current_seeder, "mix")) {
                var mix = ds_map_find_value(global.current_seeder, "mix");
                if (is_ds_map(mix) && ds_map_exists(mix, "min_tokens")) {
                    min_tokens = ds_map_find_value(mix, "min_tokens");
                }
            }
            target_label = "Target: ≥" + string(min_tokens) + " Spanish word(s)";
        }
    }

    draw_set_font(f_ui);
    draw_text(20, 120, target_label);
    draw_text(20, 140, "Used: " + string(scr_count_spanish_tokens(input_text, [])));
    draw_text(20, 160, "Register: " + scr_detect_register(input_text));
    draw_text(20, 180, "Ratio: " + string_format(scr_spanish_ratio(input_text) * 100, 0, 2) + "%");
    draw_text(20, 200, feedback_text);
    var strip_y = display_get_gui_height() - 60;
    scr_draw_accent_strip(20, strip_y);
}
