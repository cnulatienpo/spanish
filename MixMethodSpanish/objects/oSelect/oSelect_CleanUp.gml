/// @description Release dynamic section marker maps.
function oSelect_CleanUp() {
    if (is_array(section_markers)) {
        for (var i = 0; i < array_length(section_markers); i++) {
            var marker = section_markers[i];
            if (ds_exists(marker, ds_type_map)) {
                ds_map_destroy(marker);
            }
        }
    }
    section_markers = [];
}
