/// @description Prepare typing state variables.
function oTyping_Create() {
    input_text = "";
    feedback_text = "Mix time — drop some español.";

    // Register hint state
    hint_expected = scr_expected_register(global.current_seeder);
    hint_chips = scr_register_examples(hint_expected);
    hint_timer = 0;
    hint_idx = 0;
    hint_interval_ms = 2500;
}
