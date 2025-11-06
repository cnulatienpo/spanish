/// @function scr_has_errors(_list)
/// @description Return true if the provided ds_list contains any entries.
/// @param _list
function scr_has_errors(_list) {
    return (is_ds_list(_list) && ds_list_size(_list) > 0);
}
