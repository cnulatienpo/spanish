/// @function scr_struct_to_ds_map(_struct)
/// @description Recursively convert a struct into a ds_map for compatibility.
function scr_struct_to_ds_map(_struct) {
    var result = ds_map_create();
    var names = variable_struct_get_names(_struct);
    for (var i = 0; i < array_length(names); i++) {
        var key = names[i];
        var value = variable_struct_get(_struct, key);
        if (is_struct(value)) {
            var nested = scr_struct_to_ds_map(value);
            ds_map_set(result, key, nested);
        } else {
            ds_map_set(result, key, value);
        }
    }
    return result;
}
